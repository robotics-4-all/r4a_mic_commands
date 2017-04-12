#!/usr/bin/env python

# open a microphone in pyAudio and listen for taps

import pyaudio
import struct
import math
import os
import wave
import time
from RappCloud import RappPlatformAPI
import rospy
from std_msgs.msg import String

FORMAT = pyaudio.paInt16 
SHORT_NORMALIZE = (1.0/32768.0)
CHANNELS = rospy.get_param("channels")
RATE = rospy.get_param("rate")
INPUT_BLOCK_TIME = rospy.get_param("input_block_time")
dictionary = rospy.get_param("dictionary")
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)
PATH = rospy.get_param("path")

class voiceCommand:
    def __init__(self):
        self.frames = []
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.tap_threshold,self.noise_threshold = self.calibrate()
        self.hear = False
        self.ch = RappPlatformAPI()
        
        topic = rospy.get_param("rec_topic")
        self.publisher = rospy.Publisher(topic, String, queue_size=10)

    def stop(self):
        self.stream.close()

    #finds device inputs
    def find_input_device(self):
        device_index = None            
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i)   
            print( "Device %d: %s"%(i,devinfo["name"]) )

            for keyword in ["mic","input"]:
                if keyword in devinfo["name"].lower():
                    print( "Found an input: device %d - %s"%(i,devinfo["name"]) )
                    device_index = i
                    return device_index

        if device_index == None:
            print( "No preferred input found; using default input device." )

        return device_index


    #opens stream
    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(   format = FORMAT,
                                 channels = CHANNELS,
                                 rate = RATE,
                                 input = True,
                                 input_device_index = device_index,
                                 frames_per_buffer = INPUT_FRAMES_PER_BLOCK)

        return stream

    def tapDetected(self):
        print "Tap!"
    
    def unpack(self, block ):
        count = len(block)/2
        format = "%dh"%(count)
        shorts = struct.unpack( format, block )
        return shorts , count   

    def get_rms(self, block ):
    # RMS amplitude is defined as the square root of the 
    # mean over time of the square of the amplitude.
    # so we need to convert this string of bytes into 
    # a string of 16-bit samples...

    # we will get one short out for each 
    # two chars in the string.
    
        shorts , count = self.unpack( block )

    # iterate over the block.
        sum_squares = 0.0
        for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
            n = sample * SHORT_NORMALIZE
            sum_squares += n*n

        return math.sqrt( sum_squares / count )



    #computeThreshold listens to stream for $seconds seconds
    #and computes the threshold using RMS
    def computeThreshold(self, seconds):
        block_sum = 0
        counter = 0

        while seconds>0:
            block_sum += self.get_rms(self.stream.read(INPUT_FRAMES_PER_BLOCK))
            seconds -= INPUT_BLOCK_TIME
            counter += 1

        return block_sum/counter



    #calibrate compute silence and voice thresholds
    def calibrate(self):
        print("Noise calibration.BE QUIET.")
        noise_threshold = self.computeThreshold(2)
        print("Noise calibration COMPLETE.")  

        print("Command calibration.")
        tap_threshold = self.computeThreshold(2)
        print("Command calibration complete.")
        return tap_threshold , noise_threshold



    #write2WAV saves self.frames as file.wav
    def write2WAV( self ):
        waveFile = wave.open(PATH + 'file.wav', 'w')
        waveFile.setnchannels(CHANNELS)
        waveFile.setsampwidth(self.pa.get_sample_size(FORMAT))
        waveFile.setframerate(RATE)
        waveFile.writeframes(b''.join(self.frames))
        waveFile.close()
        self.frames = []

    def setHear(self, value):
        self.hear = value



    def listen(self):
        try:
            downCounter = 0
            upCounter = 0
            self.frames = []
            flag = False
            

            while self.hear and (not rospy.is_shutdown()):
                block = self.stream.read(INPUT_FRAMES_PER_BLOCK)
                amp = self.get_rms( block )
                if amp > self.tap_threshold + self.noise_threshold:
                    flag = True#heard something for first time
                    #self.tapDetected()
                    downCounter = 0
                    upCounter +=1 
                else:
                    downCounter += 1
                
                if flag:
                    self.frames.append( block )
                else:
                    if len(self.frames)>3:
                        self.frames.pop( 0 )
                    self.frames.append( block )



                if upCounter > 40:#Too long record 40*0.05 = 2sec
                    print("TOO LONG RECORD")
                    break

                
                if downCounter > 20:
                    if upCounter > 1:
                        self.stream.stop_stream()
                        self.write2WAV()
                        print('File recorded.')
                        self.stream.start_stream()
                        time.sleep(0.1)

                        downCounter = 0
                        upCounter = 0
                        self.hear = False
                    else:
                        downCounter = 0
                        upCounter = 0
                        self.frames = []
                    flag = False

        except KeyboardInterrupt:
            self.stop()
            return False
        return True


    def voiceRec(self):
        response = self.ch.speechRecognitionSphinx(PATH + "file.wav", "nao_wav_1_ch", 'en', dictionary)
        str_response = str(response.get('words'))
        if len(response.get('words')) != 1:
            return ''
        self.publisher.publish(str_response)

        return str_response


if __name__ == "__main__":
    node = rospy.get_param("rec_node")
    rospy.init_node(node, anonymous=True)
    tt = voiceCommand()
    while not rospy.is_shutdown():
        try:
            print("New Recording.")
            tt.setHear(True)
            tt.listen()
            res = tt.voiceRec()
        except KeyboardInterrupt:
            tt.stop()
            break



