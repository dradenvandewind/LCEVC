rm -rf /tmp/*.dot
export GST_DEBUG_DUMP_DOT_DIR=/tmp
GST_DEBUG=xevddec:6 gst-launch-1.0 filesrc location=$1 ! y4mdec ! videoconvert ! video/x-raw,width=$2,height=$3,format=I420 ! identity silent=false ! xeveenc rc_mode=1 hash=1 info-sei=1 keyint-max=10 preset=1 profile=0 bitrate=3000 ! capssetter caps="video/x-evc" ! queue ! xevddec hash=1 bit-depth=10 ! filesink location=$4
