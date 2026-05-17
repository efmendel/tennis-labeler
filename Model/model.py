import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models
import os
from sklearn.model_selection import train_test_split

GOOGLE_DRIVE_VIDEO_PATH = '/Users/kamranbastani/Library/CloudStorage/GoogleDrive-kmbastani@yahoo.com/My Drive/Forehand_data/videos'
EXCEL_FILE = 'video_indexing.xlsx'
IMG_SIZE = (224, 224)  # This is the "Downsampled" resolution
BATCH_SIZE = 8

def get_label(frame_idx, row):
    if row['unit_turn_frame'] <= frame_idx < row['backswing_frame']: return 1
    if row['backswing_frame'] <= frame_idx < row['forward_swing_frame']: return 2
    if row['forward_swing_frame'] <= frame_idx < row['follow_through_frame']: return 3
    if row['follow_through_frame'] <= frame_idx < row['swing_end_frame']: return 4
    return 0

def build_tennis_phase_classifier(input_shape=(5, 224, 224, 3)):
    # 1. Feature Extractor (The "Spatial" part)
    # Using MobileNetV2 for speed and efficiency on your Mac
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=input_shape[1:], 
        include_top=False, 
        pooling='avg'
    )
    base_model.trainable = False 

    model = models.Sequential([
        # Wrap the CNN to process all 5 frames in parallel
        layers.TimeDistributed(base_model, input_shape=input_shape, name="spatial_features"),

        # 2. Temporal Analysis (The "Motion" part)
        # Filters look for patterns across the 5 frames
        layers.Conv1D(filters=128, kernel_size=3, padding='same', activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.3),
        
        layers.Conv1D(filters=64, kernel_size=3, padding='same', activation='relu'),
        layers.GlobalAveragePooling1D(), # Squash the temporal dimension

        # 3. Classification (The "Decision" part)
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        # 5 units for: 0=None, 1=Unit Turn, 2=Backswing, 3=Forward, 4=Follow Through
        layers.Dense(5, activation='softmax', name="phase_output")
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy', # Matches integer labels (0, 1, 2...)
        metrics=['accuracy']
    )
    
    return model

def frame_generator(dataframe):
    # This function now correctly accepts the split dataframe
    for _, row in dataframe.iterrows():
        video_path = os.path.join(GOOGLE_DRIVE_VIDEO_PATH, row['video_name'])
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            continue

        for i in range(int(row['swing_start_frame']), int(row['swing_end_frame'])):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, i - 2))
            sequence = []
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    sequence.append(np.zeros((*IMG_SIZE, 3), dtype=np.float32))
                else:
                    frame = cv2.resize(frame, IMG_SIZE, interpolation=cv2.INTER_AREA)
                    frame = tf.keras.applications.mobilenet_v2.preprocess_input(frame)
                    sequence.append(frame)
            
            yield np.array(sequence), get_label(i, row)
        cap.release()

# Train test split by video name to ensure the model is not being tested on overlapping part of videos
df = pd.read_excel('video_indexing.xlsx')

# Get unique video names to ensure a clean split
unique_videos = df['video_name'].unique()

train_vids, test_vids = train_test_split(unique_videos, test_size=0.2, random_state=42)

df_train = df[df['video_name'].isin(train_vids)]
df_test = df[df['video_name'].isin(test_vids)]

train_ds = tf.data.Dataset.from_generator(
    lambda: frame_generator(df_train),
    output_signature=(
        tf.TensorSpec(shape=(5, 224, 224, 3), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int32)
    )
).shuffle(100).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

test_ds = tf.data.Dataset.from_generator(
    lambda: frame_generator(df_test),
    output_signature=(
        tf.TensorSpec(shape=(5, 224, 224, 3), dtype=tf.float32),
        tf.TensorSpec(shape=(), dtype=tf.int32)
    )
).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

total_frames = sum(df_train['swing_end_frame'] - df_train['swing_start_frame'])
steps = total_frames // BATCH_SIZE

# Initialize the model
model = build_tennis_phase_classifier()
model.summary()

# Class weights calculated based on the inverse frequency of the number of frames for each class
class_weights = {0: 0.6, 1: 1.97, 2: 0.81, 3: 2.57, 4: 0.84}
model.fit(train_ds, epochs=5, steps_per_epoch=100, class_weight=class_weights)
results = model.evaluate(test_ds, steps=50)
print(f"Test Loss: {results[0]:.4f}")
print(f"Test Accuracy: {results[1]*100:.2f}%")