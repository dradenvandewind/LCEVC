## This project enables the encoding and decoding of video content in EVC (Essential Video Coding) format. Two GStreamer plugins have been developed based on the xeve and xevd libraries:
## xeveenc : A Gstreamer Plugin for EVC encoder
## xevddec : A Gstreamer Plugin for EVC decoder


This plugin are still under development and will continue to improve by:
1 :exposing additional encoder properties
2 :accept other chrominance formats
3 ..

## Prerequisites


Everything is specified in the dockerfile.
Just run this command: docker-compose build && docker compose run gst-worker bash



EVC encoder libraries currently supported by the plugin are:
  - XEVE v0.5.1 - https://github.com/mpeg5/xeve

EVC decoder libraries currently supported by the plugin are:
  - XEVD v0.5.0 - https://github.com/mpeg5/xevd.git


In the next section, we demonstrate the usage of the plugins

## Usage of the xeveenc plugin

```
    gst-inspect-1.0 xeveenc
```
Following are the pad templates supported by the plugin:

```
Pad Templates:
  SINK template: 'sink'
    Availability: Always
    Capabilities:
      video/x-raw
                 format: { (string)I420, (string)I420_10LE }
                  width: [ 1, 2147483647 ]
                 height: [ 1, 2147483647 ]
              framerate: [ 0/1, 2147483647/1 ]
  
  SRC template: 'src'
    Availability: Always
    Capabilities:
      video/x-evc
                  width: [ 1, 2147483647 ]
                 height: [ 1, 2147483647 ]
              framerate: [ 0/1, 2147483647/1 ]
          stream-format: byte-stream
              alignment: au

```



Following are the supported element properties:
```
Element Properties:

  bitrate             : Target bitrate in bps
                        flags: readable, writable
                        Integer. Range: 1000 - 20000 Default: 2000 
  
  crf                 : Constant Rate Factor for quality-based encoding (0 = auto, 10-49 range)
                        flags: readable, writable
                        Integer. Range: 10 - 49 Default: 12 
  
  hash                : Embed picture signature (HASH) for conformance checking in decoding (0 = auto)
                        flags: readable, writable
                        Integer. Range: 0 - 1 Default: 0 
  
  info-sei            : Embed SEI messages identifying encoder parameters (0 = no, 1 = yes)
                        flags: readable, writable
                        Integer. Range: 0 - 1 Default: 1 
  
  keyint-max          : Maximum interval between I-frames (default 30)
                        flags: readable, writable
                        Integer. Range: 1 - 300 Default: 5 
  
  min-force-key-unit-interval: Minimum interval between force-keyunit requests in nanoseconds
                        flags: readable, writable
                        Unsigned Integer64. Range: 0 - 18446744073709551615 Default: 0 
  
  name                : The name of the object
                        flags: readable, writable
                        String. Default: "xeveenc0"
  
  parent              : The parent of the object
                        flags: readable, writable
                        Object of type "GstObject"
  
  preset              : XEVE preset to use (0 = Default, 1 = Fast, 2 = medium 3 = slow 4 = placebo)
                        flags: readable, writable
                        Integer. Range: 0 - 4 Default: 0 
  
  profile             : XEVE profile to use (0 = Baseline, 1 = Main)
                        flags: readable, writable
                        Integer. Range: 0 - 1 Default: 0 
  
  qos                 : Handle Quality-of-Service events from downstream
                        flags: readable, writable
                        Boolean. Default: false
  
  qp                  : Quantization Parameter (0 = auto)
                        flags: readable, writable
                        Integer. Range: 1 - 51 Default: 22 
  
  rc-mode             : Rate Control Mode (0 = CQP, 1 = ABR, 2 = CRF)
                        flags: readable, writable
                        Enum "GstXeveEncRCMode" Default: 0, "cqp"
                           (0): cqp              - Constant QP
                           (1): abr              - Average Bitrate
                           (2): crf              - Constant Rate Factor
```



## Usage of the xevddec plugin

```
    gst-inspect-1.0 xevddec
```
Following are the pad templates supported by the plugin:

```
Pad Templates:
  SINK template: 'sink'
    Availability: Always
    Capabilities:
      video/x-evc
          stream-format: byte-stream
  
  SRC template: 'src'
    Availability: Always
    Capabilities:
      video/x-raw
                 format: { (string)I420_10LE }
                  width: [ 16, 8192 ]
                 height: [ 16, 4320 ]
              framerate: [ 0/1, 300/1 ]


```

Following are the supported element properties:
```
Element Properties:

  automatic-request-sync-point-flags: Flags to use when automatically requesting sync points
                        flags: readable, writable
                        Flags "GstVideoDecoderRequestSyncPointFlags" Default: 0x00000003, "corrupt-output+discard-input"
                           (0x00000001): discard-input    - GST_VIDEO_DECODER_REQUEST_SYNC_POINT_DISCARD_INPUT
                           (0x00000002): corrupt-output   - GST_VIDEO_DECODER_REQUEST_SYNC_POINT_CORRUPT_OUTPUT
  
  automatic-request-sync-points: Automatically request sync points when it would be useful
                        flags: readable, writable
                        Boolean. Default: false
  
  bit-depth           : Bit depth of the video (default 8)
                        flags: readable, writable
                        Integer. Range: 8 - 10 Default: 8 
  
  discard-corrupted-frames: Discard frames marked as corrupted instead of outputting them
                        flags: readable, writable
                        Boolean. Default: false
  
  hash                : Enable/disable hash for picture signature (0 = no, 1 = yes, default )
                        flags: readable, writable
                        Integer. Range: 0 - 1 Default: 0 
  
  max-errors          : Max consecutive decoder errors before returning flow error
                        flags: readable, writable
                        Integer. Range: -1 - 2147483647 Default: -1 
  
  min-force-key-unit-interval: Minimum interval between force-keyunit requests in nanoseconds
                        flags: readable, writable
                        Unsigned Integer64. Range: 0 - 18446744073709551615 Default: 0 
  
  name                : The name of the object
                        flags: readable, writable
                        String. Default: "xevedec0"
  
  parent              : The parent of the object
                        flags: readable, writable
                        Object of type "GstObject"
  
  qos                 : Handle Quality-of-Service events from downstream
                        flags: readable, writable
                        Boolean. Default: true

```






To ensure compatibility with transport streams, the tsdemux and mpegtsmux plugins have been modified to support the video/x-evc codec.

To test the element, a GStreamer tool named ‘gst-launch’ can be used to test a simple pipeline as shown in figure below. 

![example pipeline](/images/main_pipeline_raw_to_ts_raw.png)
 

evc + Ts stream :
```
python3 gst_pipeline_to_test_ts_features.py [input_file] [width] [height] [output_file] [debug_level]"
```
 gst_pipeline_to_test_ts_features.py akiyo_cif.y4m 352 288 akiyo_cif_after.yuv 3

![example pipeline](/images/end_to_end_raw_to_raw.png)


evc raw to raw  :
```
./end_to_end_raw_to_raw.sh akiyo_cif.y4m 352 288 akiyo_cif_after.yuv
```


