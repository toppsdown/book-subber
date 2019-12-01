import subprocess as sp
import sys
import numpy

FFMPEG_BIN = "ffmpeg"

print 'ASplit.py <src.mp3> <silence duration in seconds> <thresheshold amplitude 0.0 .. 1.0>'

src = sys.argv[1]
duration_s = float(sys.argv[2])

max_amplitude = 65535
threshold = int(float(sys.argv[3]) * max_amplitude)

f = open('%s-out_revised.txt' % src, 'wb')

sample_rate = 22050
num_samples_in_set = duration_s * sample_rate
buflen = int(num_samples_in_set     * 2)
#            t * rate * 16 bits

last_sample_set = numpy.arange(1, dtype='int16')
# just a dummy array for the first chunk

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

    raw = pipe.stdout.read(buflen)
    if raw == '' :
        tf = False
        break

    current_sample_set = numpy.fromstring(raw, dtype = "int16")

    rng = numpy.concatenate([last_sample_set, current_sample_set])
    max_amplitude = numpy.amax(rng)
    if max_amplitude <= threshold :
        # the peak in this range is less than the threshold value
        trng = (rng <= threshold) * 1
        # effectively a pass filter with all samples <= thr set to 0 and > thr set to 1
        num_samples_below_threshold = numpy.sum(trng)
        # i.e. simply (naively) check how many 1's there were
        if num_samples_below_threshold >= num_samples_in_set :
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