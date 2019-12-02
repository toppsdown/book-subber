python ./ASplit_mac.py ./test_media/book_sample.m4a 0.1 0.1
python ./ASplit_revised.py ./test_media/book_sample.m4a 100 0.1
echo "Diff:"
diff ./test_media/book_sample.m4a-out_original.txt ./test_media/book_sample.m4a-out_revised.txt