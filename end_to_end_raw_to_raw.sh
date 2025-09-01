rm -rf /tmp/*.dot
GST_DEBUG=xevddec:6 gst-launch-1.0 filesrc location=./akiyo_cif.y4m ! y4mdec ! videoconvert ! video/x-raw,width=352,height=288,format=I420 ! identity silent=false ! xeveenc rc_mode=1 hash=1 info-sei=1 keyint-max=10 preset=1 profile=0 bitrate=3000 ! capssetter caps="video/x-lvc1" ! queue ! xevddec hash=1 bit-depth=10 ! filesink location=./end_to_end.yuv
