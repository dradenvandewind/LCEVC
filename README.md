# LCEVC



This project enables the encoding and decoding of video content in LCEVC (Low Complexity Enhancement Video Coding) format. Two GStreamer plugins have been developed based on the xeve and xevd libraries:

xeveenc: LCEVC encoding plugin
xevddec: LCEVC decoding plugin

These plugins can be inspected using the following commands:
gst-inspect-1.0 xeveenc
gst-inspect-1.0 xevddec

To ensure compatibility with transport streams, the tsdemux and mpegtsmux plugins have been modified to support the video/x-lvc1 codec.

