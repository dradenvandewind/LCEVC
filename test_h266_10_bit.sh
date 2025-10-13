GST_DEBUG=4   gst-launch-1.0 videotestsrc ! video/x-raw,format=I420_10LE, width=256,height=256 ! h266enc bitrate=1000000 ! filesink   location=videotestsrc.266
