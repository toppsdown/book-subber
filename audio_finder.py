# Based on: https://stackoverflow.com/a/57126101
# Goals:
#  - fix bugs
#  - output timestamps for each line of audio for consumption by othe program

import subprocess as sp
import sys
import numpy
import pdb

FFMPEG_BIN = "ffmpeg"
OUTPUT_FORMAT = 'ffmpeg -i "%s" -ss %f -to %f -c copy -y "%s-p%04d.m4a"\r\n'

def output_string(audio_type, start_s, end_s):
    return '[%s,%f,%f]\n' % (audio_type, start_s, end_s)


print 'audio_finder.py <src.m4a> <silence duration in miliseconds> <thresheshold amplitude 0.0 .. 1.0>'

src = sys.argv[1]
duration_ms = float(sys.argv[2])
duration_s = duration_ms/1000

max_amplitude = 65535/2
threshold = int(float(sys.argv[3]) * max_amplitude)

f = open('%s-audio_timestamps.txt' % src, 'wb')

sample_rate = 22050
num_samples_in_set = duration_s * sample_rate

buflen = int(num_samples_in_set * 2)
#            t * rate * 16 bits

# s16le audiotype:
# PCM signed 16-bit little-endian
# Represents the waveform as a series of values from 0-65536
# if sample is signed, sample range -32768-32767 midpoint is 0

command = [ FFMPEG_BIN,
        '-i', src,
        '-f', 's16le',
        '-acodec', 'pcm_s16le',
        '-ar', str(sample_rate), # ouput sampling rate
        '-ac', '1', # '1' for mono
        '-']        # - output to stdout

pipe = sp.Popen(command, stdout=sp.PIPE, bufsize=10**8)

current_processing_timestamp = 0
sample_start_timestamp = 0
audio_segment_count = 1

is_current_silence = None
is_past_silence = None

while True :

    raw = pipe.stdout.read(buflen)

    # If end of file, close program
    if raw == '' :
        f.write(OUTPUT_FORMAT % (src, sample_start_timestamp, current_processing_timestamp, src, audio_segment_count))
        break

    # when 2 bytes are used for audio samples, need to order bytes
    # Example: 0x9A8B => 1001 1010 1000 1011
    # little-endian: 8B, 9A => [1000 1011],[1001 1010]
    # big-endian: 9A, 8B => [1001 1010], [1000 1011]
    # numpy.fromstring("\x02\x01", dtype = "int16") # => 258
    # numpy.fromstring("\x02\x02", dtype = "int16") # => 514
    # numpy.fromstring("\x00\x80", dtype = "int16") # => -32768
    # numpy.fromstring("\x00\x80\x00\x80", dtype = "int16") # => [-32768,-32768]
    current_sample_set = numpy.fromstring(raw, dtype = "int16")

    # Because this is a waveform, each sample is just volume
    # Get the maximum absolute value within the range
    max_amplitude = numpy.amax(current_sample_set)

    # Threshold is calculated based on percentage of range
    # the peak in this range is less than the thresheshold value
    if max_amplitude <= threshold :
        is_current_silence = True
    else:
        is_current_silence = False

    if is_current_silence != is_past_silence:
        audio_type = "silence" if is_past_silence else "audio"
        sample_end_timestamp = current_processing_timestamp + duration_s
        f.write(OUTPUT_FORMAT % (src, sample_start_timestamp, sample_end_timestamp, src, audio_segment_count))
        f.write(output_string(audio_type, sample_start_timestamp, sample_end_timestamp))

        # move to next section of audio
        sample_start_timestamp = sample_end_timestamp
        audio_segment_count += 1
        is_past_silence = is_current_silence

    # move to next sample
    current_processing_timestamp += duration_s


f.close()