import subprocess as sp
import sys
import numpy

FFMPEG_BIN = "ffmpeg"

print 'ASplit.py <src.mp3> <silence duration in miliseconds> <thresheshold amplitude 0.0 .. 1.0>'

src = sys.argv[1]
duration_ms = float(sys.argv[2])
duration_s = duration_ms/1000

max_amplitude = 65535
threshold = int(float(sys.argv[3]) * max_amplitude)

f = open('%s-out_revised.txt' % src, 'wb')

sample_rate = 22050
num_samples_in_set = duration_s * sample_rate

# create a buffer length that can take two samples of given duration
buflen = int(num_samples_in_set     * 2)
#            t * rate * 16 bits

last_sample_set = numpy.arange(1, dtype='int16')
# just a dummy array for the first chunk


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

tf = True
current_processing_timestamp = 0
sample_start_timestamp = 0
audio_segment_count = 0

while tf :

    # grab 2x sample set duration from the pipe
    # Eg. if duration is 1 sec, take two seconds of audio

    raw = pipe.stdout.read(buflen)

    # If end of file, close program
    if raw == '' :
        tf = False
        break

    # when 2 bytes are used for audio samples, need to order bytes
    # Example: 0x9A8B => 1001 1010 1000 1011
    # little-endian: 8B, 9A => [1000 1011],[1001 1010]
    # big-endian: 9A, 8B => [1001 1010], [1000 1011]
    # Does this correctly detect little endian?
    # Looks like it understand little endian correctly and it's signed
    # numpy.fromstring("\x02\x01", dtype = "int16") # => 258
    # numpy.fromstring("\x02\x02", dtype = "int16") # => 514
    # numpy.fromstring("\x00\x80", dtype = "int16") # => -32768
    # numpy.fromstring("\x00\x80\x00\x80", dtype = "int16") # => [-32768,-32768]
    current_sample_set = numpy.fromstring(raw, dtype = "int16")

    rng = numpy.concatenate([last_sample_set, current_sample_set])

    # Because this is a waveform, each sample is just volume
    # Get the maximum absolute value within the range
    max_amplitude = numpy.amax(rng)

    # Threshold is calculated based on percentage of range
    # the peak in this range is less than the thresheshold value
    if max_amplitude <= threshold :
        num_samples_below_threshold = numpy.size(rng)
        audio_segment_count += 1
        sample_end_timestamp = current_processing_timestamp + duration_s * 0.5
        print max_amplitude, num_samples_below_threshold, num_samples_in_set, sample_end_timestamp
        f.write('ffmpeg -i "%s" -ss %f -to %f -c copy -y "%s-p%04d.m4a"\r\n' % (src, sample_start_timestamp, sample_end_timestamp, src, audio_segment_count))
        sample_start_timestamp = sample_end_timestamp

    current_processing_timestamp += duration_s

    last_sample_set = current_sample_set

audio_segment_count += 1
f.write('ffmpeg -i "%s" -ss %f -to %f -c copy -y "%s-p%04d.m4a"\r\n' % (src, sample_start_timestamp, current_processing_timestamp, src, audio_segment_count))
f.close()