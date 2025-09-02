# LCEVC



This project enables the encoding and decoding of video content in LCEVC (Low Complexity Enhancement Video Coding) format. Two GStreamer plugins have been developed based on the xeve and xevd libraries:

xeveenc: LCEVC encoding plugin
xevddec: LCEVC decoding plugin

These plugins can be inspected using the following commands:
gst-inspect-1.0 xeveenc
gst-inspect-1.0 xevddec

To ensure compatibility with transport streams, the tsdemux and mpegtsmux plugins have been modified to support the video/x-lvc1 codec.

You can try it with test script python3 gst_pipeline_to_test_ts_features.py [input_file] [width] [height] [output_file] [debug_level]"

 gst_pipeline_to_test_ts_features.py akiyo_cif.y4m 352 288 akiyo_cif_after.yuv 3


You can display diagramm pipeline with dot file in /tmp directory
