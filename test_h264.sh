gst-launch-1.0 -v videotestsrc ! x264enc qp-min=18 ! mpegtsmux ! udpsink port=10000 host=127.0.0.1

