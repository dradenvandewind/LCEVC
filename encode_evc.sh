#GST_DEBUG=xeveenc:5 gst-launch-1.0 videotestsrc num-buffers=45 ! videoconvert ! video/x-raw,width=352,height=288,framerate=30/1,format=I420 ! xeveenc ! fakesink
GST_DEBUG=xeveenc:5 gst-launch-1.0 filesrc location=$1 ! y4mdec ! videoconvert ! video/x-raw,width=352,height=288,format=I420 ! identity silent=false ! xeveenc ! filesink location=$2
