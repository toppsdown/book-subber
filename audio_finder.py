# Based on: https://stackoverflow.com/a/57126101
# Goals:
#  - fix bugs
#  - output timestamps for each line of audio for consumption by othe program

import subprocess as sp
import sys
import numpy
import pdb
from circle_buffer import CircleBuffer

FFMPEG_BIN = "ffmpeg"
OUTPUT_FORMAT = 'ffmpeg -i "%s" -ss %f -to %f -c copy -y "%s-p%04d.m4a"\r\n'

print 'audio_finder.py <src.m4a> <silence duration in miliseconds> <granularity ms> <thresheshold amplitude 0.0 .. 1.0>'

def output_to_file(f,audio_type,src, start_s, end_s, file_count):
    # if audio_type == "audio":
        # f.write(OUTPUT_FORMAT % (src, start_s, end_s, src, file_count))
    f.write('[%s,%f,%f]\n' % (audio_type, start_s, end_s))

src = sys.argv[1]

# Note, if granularity doesn't divide neatly into duration
# duration will get shorter from downrounding in duration_ms/granularity_ms
duration_ms = int(sys.argv[2])
granularity_ms = int(sys.argv[3])

max_amplitude = 65535/2
threshold = int(float(sys.argv[4]) * max_amplitude)

f = open('%s-audio_timestamps.txt' % src, 'wb')

# there's a problem here with the granularity.  If it doesn't neatly divide 22050
# then it causes problems.  calc: 50/1000 => 1/20.  22050/20 => 1102.5
# So what works?
# Prime factors 22050: 2 * 3 * 3 * 5 * 5 * 7 * 7
# Prime factors 1000: 2 * 2 * 2 * 5 * 5 * 5
# Common factors: 2 * 5 * 5

acceptable_granularities = [500, 200, 100, 40, 20]
if not granularity_ms in acceptable_granularities:
    sys.exit("Granularity must be one of: 500, 200, 100, 40, 20")

if granularity_ms > duration_ms:
    sys.exit("Granularity cannot be larger than duration")

sample_rate = 22050 # per second
granularity_s = granularity_ms/1000.0
analysis_buffer_size = duration_ms/granularity_ms

num_samples_in_set = granularity_s * sample_rate

buflen = int(num_samples_in_set * 2)
#            t * rate * 16 bits

# Total analysis buffer is the duration, each section is the granularity
circle_buffer_size = analysis_buffer_size
audio_analysis_buffer = CircleBuffer(circle_buffer_size)

# preload the circlebuffer with empty data
for x in range(circle_buffer_size-1):
    audio_analysis_buffer.insert([0])

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
audio_type = ''

is_current_silence = None
is_past_silence = None

while True :
    raw = pipe.stdout.read(buflen)

    # If end of file, close program
    if raw == '' :
        # Probably need to increase the processing time to the end of the file
        output_to_file(f,audio_type,src, sample_start_timestamp, current_processing_timestamp, audio_segment_count)
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
    audio_analysis_buffer.insert(current_sample_set)

    # Because this is a waveform, each sample is just volume
    # Get the maximum absolute value within the range
    analysis_range = numpy.concatenate(audio_analysis_buffer.data)
    max_amplitude = numpy.amax(analysis_range)

    # Threshold is calculated based on percentage of range
    # the peak in this range is less than the threshold value
    if max_amplitude <= threshold :
        is_current_silence = True
    else:
        is_current_silence = False

    if is_past_silence == None:
        is_past_silence = is_current_silence

    if is_current_silence != is_past_silence:
        audio_type = "silence" if is_past_silence else "audio"
        sample_end_timestamp = current_processing_timestamp + granularity_s
        output_to_file(f,audio_type,src, sample_start_timestamp, current_processing_timestamp, audio_segment_count)

        # move to next section of audio
        sample_start_timestamp = sample_end_timestamp
        audio_segment_count += 1
        is_past_silence = is_current_silence

    # move to next sample
    current_processing_timestamp += granularity_s


f.close()