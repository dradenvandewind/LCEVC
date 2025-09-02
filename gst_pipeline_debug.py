#!/usr/bin/env python3
"""
GStreamer Pipeline Script utilisant ElementFactory pour encodage/décodage XEVE/XEVD
Usage: python3 gst_pipeline.py [input_file] [width] [height] [debug_level]
"""

import gi
import sys
import os
import signal
import threading
import time
from pathlib import Path

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
# Set environment variable to specify where to save dot files
os.environ['GST_DEBUG_DUMP_DOT_DIR'] = '/tmp/'

class GstPipelineRunner:
    def __init__(self, input_file, width, height, output_file, debug_level="3"):
        # Initialisze GStreamer
        Gst.init(None)
        
        # debug Configuration
        self.debug_level = debug_level
        os.environ['GST_DEBUG'] = debug_level
        os.environ['GST_DEBUG_NO_COLOR'] = '1'
        
        # Specific debug for caps negotiations
        if int(debug_level) >= 4:
            os.environ['GST_DEBUG'] = f"GST_CAPS:5,GST_NEGOTIATION:5,GST_PADS:5,tsdemux:5,xeveenc:5,xevddec:5,{debug_level}"
        
        # Variables
        self.pipeline = None
        self.loop = None
        self.is_running = False
        self.elements = {}
        
        # Fichiers et paramètres vidéo
        self.input_file = input_file
        self.width = width
        self.height = height
        self.output_file = output_file
        
    def create_element(self, factory_name, element_name=None):
        """Create a GStreamer element with verification"""
        if element_name is None:
            element_name = factory_name
            
        factory = Gst.ElementFactory.find(factory_name)
        if not factory:
            raise Exception(f"Factory '{factory_name}' not found")
            
        element = factory.create(element_name)
        if not element:
            raise Exception(f"Unable to create element '{factory_name}'")
            
        self.elements[element_name] = element
        return element
    
    def create_pipeline(self):
        """Create the GStreamer pipeline with ElementFactory"""
        try:
            # Create pipeline
            self.pipeline = Gst.Pipeline.new("main-pipeline")
            
            # Create elements
            print("Creating elements...")
            
            # Source
            filesrc = self.create_element("filesrc", "source")
            filesrc.set_property("location", self.input_file)
            
            # Y4M decoder
            y4mdec = self.create_element("y4mdec", "y4m_decoder")
            
            # video Conversion 
            videoconvert = self.create_element("videoconvert", "converter")
            
            # Caps filter for RAW format
            capsfilter_raw = self.create_element("capsfilter", "caps_raw")
            caps_raw = Gst.Caps.from_string(f"video/x-raw,width={self.width},height={self.height},format=I420")
            capsfilter_raw.set_property("caps", caps_raw)
            
            # Identity for debug
            identity = self.create_element("identity", "identity")
            identity.set_property("silent", False)
            
            # XEVE encoder
            xeveenc = self.create_element("xeveenc", "encoder")
            xeveenc.set_property("rc_mode", 1)
            xeveenc.set_property("hash", 1)
            xeveenc.set_property("info-sei", 1)
            xeveenc.set_property("keyint-max", 10)
            xeveenc.set_property("preset", 1)
            xeveenc.set_property("profile", 0)
            xeveenc.set_property("bitrate", 3000)
            
            # Capssetter for LVC1
            capssetter = self.create_element("capssetter", "caps_setter")
            caps_lvc1 = Gst.Caps.from_string("video/x-lvc1")
            capssetter.set_property("caps", caps_lvc1)
            
            # Queue
            queue = self.create_element("queue", "queue")
            
            # MPEG-TS muxer
            mpegtsmux = self.create_element("mpegtsmux", "muxer")
            
            # MPEG-TS demuxer
            tsdemux = self.create_element("tsdemux", "demuxer")
            
            #  XEVD decoder
            xevddec = self.create_element("xevddec", "decoder")
            xevddec.set_property("hash", 1)
            xevddec.set_property("bit-depth", 10)
            
            # Sink
            filesink = self.create_element("filesink", "sink")
            filesink.set_property("location", self.output_file)
            
            # add elements to pipeline 
            print("add elements to pipeline...")
            elements_to_add = [
                filesrc, y4mdec, videoconvert, capsfilter_raw, identity,
                xeveenc, capssetter, queue, mpegtsmux, tsdemux, xevddec, filesink
            ]
            
            for element in elements_to_add:
                self.pipeline.add(element)
            
            # Link static element (up to tsdemux)
            print("Link static element ...")
            # Link static element (up to tsdemux) 
            print("Link static element  step after step ...")

            # Link elements one by one
            if not filesrc.link(y4mdec):
                raise Exception("Failed to link filesrc -> y4mdec")

            if not y4mdec.link(videoconvert):
                raise Exception("Failed to link y4mdec -> videoconvert")

            if not videoconvert.link(capsfilter_raw):
                raise Exception("Failed to link videoconvert -> capsfilter_raw")

            if not capsfilter_raw.link(identity):
                raise Exception("Failed to link capsfilter_raw -> identity")

            if not identity.link(xeveenc):
                raise Exception("Failed to link identity -> xeveenc")

            if not xeveenc.link(capssetter):
                raise Exception("Failed to link xeveenc -> capssetter")

            if not capssetter.link(queue):
                raise Exception("Failed to link capssetter -> queue")

            if not queue.link(mpegtsmux):
                raise Exception("Failed to link queue -> mpegtsmux")

            print("All static elements linked successfully")


            
            # Liaison mpegtsmux -> tsdemux
            print("Linking mpegtsmux -> tsdemux...")
            if not Gst.Element.link(mpegtsmux, tsdemux):
                raise Exception("unable to link mpegtsmux -> tsdemux")
            
            # Handle dynamic pads from tsdemux
            tsdemux.connect("pad-added", self.on_pad_added)
            tsdemux.connect("no-more-pads", self.on_no_more_pads)
            
            Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "pipeline_ts_created")
            
            return True
            
        except Exception as e:
            print(f"Pipeline creation error: {e}")
            return False
    
    def on_pad_added(self, element, pad):
        """Callback for dynamics pads from tsdemux"""
        pad_name = pad.get_name()
        print(f"🔗 New pads added: {pad_name}")
        
        # Get current caps from source pad
        src_caps = pad.get_current_caps()
        if not src_caps or src_caps.is_empty():
            print(f"⚠️ no caps available on pad {pad_name}")
            return
        
        print(f"📄  source Caps: {src_caps.to_string()}")
        
        # Get decoder and its sink pad
        decoder = self.elements.get("decoder")
        if not decoder:
            print("❌ Decoder pad not found")
            return
            
        decoder_sink_pad = decoder.get_static_pad("sink")
        if not decoder_sink_pad:
            print("❌ sink pad not found")
            return
        
        # Check caps accepted by decoder
        
        decoder_sink_caps = decoder_sink_pad.query_caps(None)
        print(f"📄 Caps accepted by decoder: {decoder_sink_caps.to_string()}")
        
        # Checks caps compatibility
        intersection = src_caps.intersect(decoder_sink_caps)
        if intersection.is_empty():
            print("❌ formats are not compatible")
            print(f"Source: {src_caps.to_string()}")
            print(f"Decoder: {decoder_sink_caps.to_string()}")
            return
        
        print(f"✅ Compatibles formats: {intersection.to_string()}")
        
        # Attempt to link
        print(f"🔄 Attempting to link  {pad_name} -> decoder...")
        link_result = pad.link(decoder_sink_pad)
        
        if link_result == Gst.PadLinkReturn.OK:
            print("✅ Link sucessfull")
            
            # Link décoder to filesink
            filesink = self.elements.get("sink")
            if filesink and Gst.Element.link(decoder, filesink):
                print("✅ Pipeline fully connected!")
            else:
                print("❌ Error linking decoder -> filesink")
        else:
            print(f"❌ Link error: {link_result}")
                        
    def on_no_more_pads(self, element):
        """Callback when all pads are created """
        print("all dynamics pads have been created")
    
    def on_message(self, bus, message):
        """GStreamer bus message handler"""
        mtype = message.type
        
        if mtype == Gst.MessageType.EOS:
            print("End of stream (EOS)")
            self.stop()
            
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}")
            print(f"Debug: {debug}")
            
            # Display problematic elements
            if message.src:
                print(f"Error source: {message.src.get_name()}")
            
            self.stop()
            
        elif mtype == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            print(f"Warning: {err}")
            
        elif mtype == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                print(f" pipeline state: {old_state.value_name} -> {new_state.value_name}")
                pipeline_name="main_pipeline_" + str(old_state.value_name) + "_" + str(new_state.value_name)
                
                Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, pipeline_name)

            else:
                # Individual element states
                old_state, new_state, pending_state = message.parse_state_changed()
                element_name = message.src.get_name() if message.src else "unknown"
                print(f"State {element_name}: {old_state.value_name} -> {new_state.value_name}")
                
        elif mtype == Gst.MessageType.ELEMENT:
            # Elements messages
            struct = message.get_structure()
            if struct:
                element_name = message.src.get_name() if message.src else "unknown"
                print(f"Message from '{element_name}': {struct.get_name() if hasattr(struct, 'get_name') else 'unknown'}")
                
        elif mtype == Gst.MessageType.STREAM_STATUS:
            # Streams status
            status_type, owner = message.parse_stream_status()
            owner_name = owner.get_name() if owner else "unknown"
            print(f"Stream status from {owner_name}: {status_type.value_name}")
            
        elif mtype == Gst.MessageType.ASYNC_DONE:
            print("Pipeline ready (ASYNC_DONE)")
            
        elif mtype == Gst.MessageType.NEW_CLOCK:
            clock = message.parse_new_clock()
            print(f"New clock: {clock.get_name()}")
            
        elif mtype == Gst.MessageType.STREAM_START:
            print("stream start")
            
        elif mtype == getattr(Gst.MessageType, 'CAPS', None):   
            # caps change
            element_name = message.src.get_name() if message.src else "unknown"
            print(f"Changement de caps sur {element_name}")
            
        elif mtype == Gst.MessageType.TAG:
            # Tags/métadata
            taglist = message.parse_tag()
            element_name = message.src.get_name() if message.src else "unknown"
            print(f"Tags from {element_name}: {taglist.to_string()}")
            
        elif mtype == Gst.MessageType.BUFFERING:
            # Buffering
            percent = message.parse_buffering()
            print(f"Buffering: {percent}%")
            
        return True
    
    def check_files(self):
        """Check file existence"""
        if not Path(self.input_file).exists():
            print(f"Error : Input file '{self.input_file}' not found")
            return False
            
        # Delete output file if it exists
        if Path(self.output_file).exists():
            Path(self.output_file).unlink()
            print(f"Output file '{self.output_file}' deleted")
            
        return True
    
    def check_elements(self):
        """Check GStreamer element availability"""
        required_elements = [
            'filesrc', 'y4mdec', 'videoconvert', 'capsfilter', 'identity',
            'xeveenc', 'capssetter', 'queue', 'mpegtsmux',
            'tsdemux', 'xevddec', 'filesink'
        ]
        
        missing_elements = []
        for element in required_elements:
            factory = Gst.ElementFactory.find(element)
            if not factory:
                missing_elements.append(element)
            else:
                # Display element information
                klass = factory.get_klass()
                print(f"✓ {element}: {klass}")
        
        if missing_elements:
            print(f"Missing elements: {', '.join(missing_elements)}")
            print("Install required GStreamer plugins")
            return False
            
        return True
    
    def print_element_properties(self, element_name):
        """ Display element properties"""
        element = self.elements.get(element_name)
        if not element:
            return
            
        print(f"\nProperties of {element_name}:")
        for prop in element.list_properties():
            try:
                value = element.get_property(prop.name)
                print(f"  {prop.name}: {value} ({prop.value_type.name})")
            except:
                print(f"  {prop.name}: (unreadable)")
    
    def run(self):
        """Start the pipeline"""
        if not self.check_files():
            return False
            
        if not self.check_elements():
            return False
            
        if not self.create_pipeline():
            return False
        
        # Display properties (debug)
        if self.debug_level >= "4":
            self.print_element_properties("encoder")
            self.print_element_properties("decoder")
        
        # bus configuration
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
        # Start pipeline
        print("Start pipeline...")
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        
        if ret == Gst.StateChangeReturn.FAILURE:
            print("unable to start pipeline")
            return False
        elif ret == Gst.StateChangeReturn.ASYNC:
            print("Asynchronous startup...")
        
        # Event loop
        self.loop = GLib.MainLoop()
        self.is_running = True
        
        try:
            print("Pipeline running... (Ctrl+C to stop)")
            self.loop.run()
        except KeyboardInterrupt:
            print("\n User Interruption ")
            self.stop()
        
        return True
    
    def stop(self):
        """ Stop the pipeline"""
        if self.is_running:
            print(" Stopping pipeline...")
            self.is_running = False
            
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
                
            if self.loop:
                self.loop.quit()
    
    def get_progress(self):
        """ Display progress """
        if self.pipeline and self.is_running:
            try:
                # Query position and duration
                success_pos, position = self.pipeline.query_position(Gst.Format.TIME)
                success_dur, duration = self.pipeline.query_duration(Gst.Format.TIME)
                
                if success_pos:
                    pos_sec = position / Gst.SECOND
                    if success_dur and duration > 0:
                        dur_sec = duration / Gst.SECOND
                        progress = (position / duration) * 100
                        print(f"Progress: {pos_sec:.1f}s / {dur_sec:.1f}s ({progress:.1f}%)")
                    else:
                        print(f"Position: {pos_sec:.1f}s")
            except:
                pass

def signal_handler(signum, frame):
    """Signal handler for clean shutdown"""
    print("\nSignal received, shutting down...")
    sys.exit(0)

def print_usage():
    """Affiche l'utilisation du script"""print("Usage: python3 gst_pipeline.py [input_file] [width] [height] [output_file] [debug_level]")
    print(" input_file: Path to input file")
    print(" width: Video width")
    print(" height: Video height")
    print(" output_file: Path to output file")
    print(" debug_level: Debug level (optional, default: 3)")

def main():
    # Configuration des signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Vérification des arguments
    if len(sys.argv) < 5:
        print_usage()
        sys.exit(1)
    
    # Récupération des paramètres
    input_file = sys.argv[1]
    
    try:
        width = int(sys.argv[2])
        height = int(sys.argv[3])
    except ValueError:
        print("Erreur: width et height doivent être des nombres entiers")
        sys.exit(1)
    output_file = sys.argv[4]
    
    #Debug level from arguments
    debug_level = sys.argv[5] if len(sys.argv) > 5 else "3"
    
    print(f"Starting with parameters: input_file={input_file}, width={width}, height={height}, output_file={output_file}, debug_level={debug_level}")
    
    
    # Create and run runner
    runner = GstPipelineRunner(input_file, width, height, debug_level)
    
    # # Thread to display progress
    def progress_thread():
        while runner.is_running:
            runner.get_progress()
            time.sleep(5)
    
    progress_t = threading.Thread(target=progress_thread, daemon=True)
    progress_t.start()
    
    # Start
    success = runner.run()
    
    if success:
        print("Pipeline completed successfully")
        if Path(runner.output_file).exists():
            size = Path(runner.output_file).stat().st_size
            print(f"Output file created: {runner.output_file} ({size} bytes)")
    else:
        print("Error durung pipeline execution ")
        sys.exit(1)

if __name__ == "__main__":
    main()