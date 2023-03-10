from flask import Flask, render_template, request, redirect, url_for, Response
import numpy as np
import cv2
import keras
from keras.preprocessing.image import ImageDataGenerator
import tensorflow as tf

import warnings
from keras.callbacks import ReduceLROnPlateau
from keras.callbacks import ModelCheckpoint, EarlyStopping
warnings.simplefilter(action='ignore', category=FutureWarning)

app = Flask(__name__)
camera = cv2.VideoCapture(0)

model = keras.models.load_model("model/model.h5")
background = None
accumulated_weight = 0.75
ROI_top = 100
ROI_bottom = 400
ROI_right = 350
ROI_left = 550


word_dict2 = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L', 12: 'M',
              13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S', 19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z'}


def cal_accum_avg(frame, accumulated_weight):

    global background

    if background is None:
        background = frame.copy().astype("float")
        return None

    cv2.accumulateWeighted(frame, background, accumulated_weight)


def segment_hand(frame, threshold=20):
    global background

    diff = cv2.absdiff(background.astype("uint8"), frame)

    _, thresholded = cv2.threshold(diff, threshold, 255,
                                   cv2.THRESH_BINARY)

    # Fetching contours in the frame (These contours can be of handor any other object in foreground) …

    contours, hierarchy = cv2.findContours(
        thresholded.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # If length of contours list = 0, means we didn't get anycontours...
    if len(contours) == 0:
        return None
    else:
        # The largest external contour should be the hand
        hand_segment_max_cont = max(contours, key=cv2.contourArea)

        # Returning the hand segment(max contour) and thethresholded image of hand...
        return (thresholded, hand_segment_max_cont)


def generate_frames():
    num_frames = 0
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame = cv2.flip(frame, 1)

            frame_copy = frame.copy()

            # ROI from the frame
            roi = frame[ROI_top:ROI_bottom, ROI_right:ROI_left]

            gray_frame = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, (9, 9), 0)

            if num_frames < 70:

                cal_accum_avg(gray_frame, accumulated_weight)

                cv2.putText(frame_copy, "FETCHING BACKGROUND...PLEASE WAIT",
                            (80, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            else:
                # segmenting the hand region
                hand = segment_hand(gray_frame)

            # Checking if we are able to detect the hand...
                if hand is not None:

                    thresholded, hand_segment = hand

                    # Drawing contours around hand segment
                    cv2.drawContours(frame_copy, [hand_segment + (ROI_right,
                                                                  ROI_top)], -1, (255, 0, 0), 1)

                    thresholded = cv2.resize(thresholded, (150, 150))
                    thresholded = cv2.cvtColor(thresholded,
                                               cv2.COLOR_GRAY2RGB)
                    thresholded = np.reshape(thresholded,
                                             (1, thresholded.shape[0], thresholded.shape[1], 3))

                    # predicting the sign with probablity
                    pred = model.predict(thresholded)

                    # 2 angka dibelakang koma
                    prob = np.max(pred, axis=1).round(2)

                    cv2.putText(frame_copy, "PROBABILITY : " + str(prob),
                        (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (2, 500, 0 ), 1)    
         

                    cv2.putText(frame_copy, "PREDICTION : " + word_dict2[np.argmax(pred)],
                        (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (2, 500, 0 ), 1)


            # Draw ROI on frame_copy
            cv2.rectangle(frame_copy, (ROI_left, ROI_top), (ROI_right,
                                                            ROI_bottom), (255, 128, 0), 3)

            # incrementing the number of frames for tracking
            num_frames += 1

            # Display the frame with segmented hand
            cv2.putText(frame_copy, "",
                        (50, 50), cv2.FONT_ITALIC, 0.5, (51, 255, 51), 1)

            ret, buffer = cv2.imencode('.jpg', frame_copy)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
