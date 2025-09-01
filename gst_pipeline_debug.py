#!/usr/bin/env python3
"""
GStreamer Pipeline Script utilisant ElementFactory pour encodage/décodage XEVE/XEVD
Usage: python3 gst_pipeline.py [debug_level]
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
    def __init__(self, debug_level="3"):
        # Initialisation de GStreamer
        Gst.init(None)
        
        # Configuration du debug
        self.debug_level = debug_level
        os.environ['GST_DEBUG'] = debug_level
        os.environ['GST_DEBUG_NO_COLOR'] = '1'
        
        # Debug spécifique pour les négociations de caps
        if int(debug_level) >= 4:
            os.environ['GST_DEBUG'] = f"GST_CAPS:5,GST_NEGOTIATION:5,GST_PADS:5,tsdemux:5,xeveenc:5,xevddec:5,{debug_level}"
        
        # Variables
        self.pipeline = None
        self.loop = None
        self.is_running = False
        self.elements = {}
        
        # Fichiers
        self.input_file = "./akiyo_cif.y4m"
        self.output_file = "./end_to_end_from_ts.yuv"
        
    def create_element(self, factory_name, element_name=None):
        """Crée un élément GStreamer avec vérification"""
        if element_name is None:
            element_name = factory_name
            
        factory = Gst.ElementFactory.find(factory_name)
        if not factory:
            raise Exception(f"Factory '{factory_name}' introuvable")
            
        element = factory.create(element_name)
        if not element:
            raise Exception(f"Impossible de créer l'élément '{factory_name}'")
            
        self.elements[element_name] = element
        return element
    
    def create_pipeline(self):
        """Crée le pipeline GStreamer avec ElementFactory"""
        try:
            # Création du pipeline
            self.pipeline = Gst.Pipeline.new("main-pipeline")
            
            # Création des éléments
            print("Création des éléments...")
            
            # Source
            filesrc = self.create_element("filesrc", "source")
            filesrc.set_property("location", self.input_file)
            
            # Décodeur Y4M
            y4mdec = self.create_element("y4mdec", "y4m_decoder")
            
            # Conversion vidéo
            videoconvert = self.create_element("videoconvert", "converter")
            
            # Filtre de caps pour format RAW
            capsfilter_raw = self.create_element("capsfilter", "caps_raw")
            caps_raw = Gst.Caps.from_string("video/x-raw,width=352,height=288,format=I420")
            capsfilter_raw.set_property("caps", caps_raw)
            
            # Identity pour debug
            identity = self.create_element("identity", "identity")
            identity.set_property("silent", False)
            
            # Encodeur XEVE
            xeveenc = self.create_element("xeveenc", "encoder")
            xeveenc.set_property("rc_mode", 1)
            xeveenc.set_property("hash", 1)
            xeveenc.set_property("info-sei", 1)
            xeveenc.set_property("keyint-max", 10)
            xeveenc.set_property("preset", 1)
            xeveenc.set_property("profile", 0)
            xeveenc.set_property("bitrate", 3000)
            
            # Capssetter pour LVC1
            capssetter = self.create_element("capssetter", "caps_setter")
            caps_lvc1 = Gst.Caps.from_string("video/x-lvc1")
            capssetter.set_property("caps", caps_lvc1)
            
            # Queue
            queue = self.create_element("queue", "queue")
            
            # Muxer MPEG-TS
            mpegtsmux = self.create_element("mpegtsmux", "muxer")
            
            # Demuxer MPEG-TS
            tsdemux = self.create_element("tsdemux", "demuxer")
            
            # Décodeur XEVD
            xevddec = self.create_element("xevddec", "decoder")
            xevddec.set_property("hash", 1)
            xevddec.set_property("bit-depth", 10)
            
            # Sink
            filesink = self.create_element("filesink", "sink")
            filesink.set_property("location", self.output_file)
            
            # Ajout des éléments au pipeline
            print("Ajout des éléments au pipeline...")
            elements_to_add = [
                filesrc, y4mdec, videoconvert, capsfilter_raw, identity,
                xeveenc, capssetter, queue, mpegtsmux, tsdemux, xevddec, filesink
            ]
            
            for element in elements_to_add:
                self.pipeline.add(element)
            
            # Liaison des éléments statiques (jusqu'au tsdemux)
            print("Liaison des éléments statiques...")
            # Liaison des éléments statiques (jusqu'au tsdemux) - version pas à pas
            print("Liaison des éléments statiques pas à pas...")

            # Liaison des éléments un par un
            if not filesrc.link(y4mdec):
                raise Exception("Échec de liaison filesrc -> y4mdec")

            if not y4mdec.link(videoconvert):
                raise Exception("Échec de liaison y4mdec -> videoconvert")

            if not videoconvert.link(capsfilter_raw):
                raise Exception("Échec de liaison videoconvert -> capsfilter_raw")

            if not capsfilter_raw.link(identity):
                raise Exception("Échec de liaison capsfilter_raw -> identity")

            if not identity.link(xeveenc):
                raise Exception("Échec de liaison identity -> xeveenc")

            if not xeveenc.link(capssetter):
                raise Exception("Échec de liaison xeveenc -> capssetter")

            if not capssetter.link(queue):
                raise Exception("Échec de liaison capssetter -> queue")

            if not queue.link(mpegtsmux):
                raise Exception("Échec de liaison queue -> mpegtsmux")

            print("Tous les éléments statiques ont été liés avec succès")


            
            # Liaison mpegtsmux -> tsdemux
            print("Liaison mpegtsmux -> tsdemux...")
            if not Gst.Element.link(mpegtsmux, tsdemux):
                raise Exception("Impossible de lier mpegtsmux -> tsdemux")
            
            # Gestion des pads dynamiques du tsdemux
            tsdemux.connect("pad-added", self.on_pad_added)
            tsdemux.connect("no-more-pads", self.on_no_more_pads)
            
            Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "pipeline_ts_created")
            
            return True
            
        except Exception as e:
            print(f"Erreur création pipeline: {e}")
            return False
    
    def on_pad_added(self, element, pad):
        """Callback pour les pads dynamiques du tsdemux"""
        pad_name = pad.get_name()
        print(f"🔗 Nouveau pad ajouté: {pad_name}")
        
        # Obtention des caps actuelles du pad source
        src_caps = pad.get_current_caps()
        if not src_caps or src_caps.is_empty():
            print(f"⚠️ Aucune caps disponible sur le pad {pad_name}")
            return
        
        print(f"📄 Caps source: {src_caps.to_string()}")
        
        # Récupération du décodeur et son pad sink
        decoder = self.elements.get("decoder")
        if not decoder:
            print("❌ Decoder non trouvé")
            return
            
        decoder_sink_pad = decoder.get_static_pad("sink")
        if not decoder_sink_pad:
            print("❌ Pad sink du decoder non trouvé")
            return
        
        # Vérification des caps acceptées par le décodeur
        decoder_sink_caps = decoder_sink_pad.query_caps(None)
        print(f"📄 Caps acceptées par le décodeur: {decoder_sink_caps.to_string()}")
        
        # Vérification de la compatibilité des caps
        intersection = src_caps.intersect(decoder_sink_caps)
        if intersection.is_empty():
            print("❌ Les formats ne sont pas compatibles")
            print(f"Source: {src_caps.to_string()}")
            print(f"Decoder: {decoder_sink_caps.to_string()}")
            return
        
        print(f"✅ Formats compatibles: {intersection.to_string()}")
        
        # Tentative de liaison
        print(f"🔄 Tentative de liaison {pad_name} -> decoder...")
        link_result = pad.link(decoder_sink_pad)
        
        if link_result == Gst.PadLinkReturn.OK:
            print("✅ Liaison réussie")
            
            # Liaison du décodeur au filesink
            filesink = self.elements.get("sink")
            if filesink and Gst.Element.link(decoder, filesink):
                print("✅ Pipeline entièrement connecté!")
            else:
                print("❌ Erreur liaison decoder -> filesink")
        else:
            print(f"❌ Erreur de liaison: {link_result}")
                        
    def on_no_more_pads(self, element):
        """Callback quand tous les pads sont créés"""
        print("Tous les pads dynamiques ont été créés")
    
    def on_message(self, bus, message):
        """Gestionnaire de messages du bus GStreamer"""
        mtype = message.type
        
        if mtype == Gst.MessageType.EOS:
            print("Fin du stream (EOS)")
            self.stop()
            
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Erreur: {err}")
            print(f"Debug: {debug}")
            
            # Affichage des éléments problématiques
            if message.src:
                print(f"Source de l'erreur: {message.src.get_name()}")
            
            self.stop()
            
        elif mtype == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            print(f"Attention: {err}")
            
        elif mtype == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                print(f"État pipeline: {old_state.value_name} -> {new_state.value_name}")
                pipeline_name="main_pipeline_" + str(old_state.value_name) + "_" + str(new_state.value_name)
                
                Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, pipeline_name)

            else:
                # États des éléments individuels
                old_state, new_state, pending_state = message.parse_state_changed()
                element_name = message.src.get_name() if message.src else "unknown"
                print(f"État {element_name}: {old_state.value_name} -> {new_state.value_name}")
                
        elif mtype == Gst.MessageType.ELEMENT:
            # Messages des éléments
            struct = message.get_structure()
            if struct:
                element_name = message.src.get_name() if message.src else "unknown"
                print(f"Message de '{element_name}': {struct.get_name() if hasattr(struct, 'get_name') else 'unknown'}")
                
        elif mtype == Gst.MessageType.STREAM_STATUS:
            # Status des streams
            status_type, owner = message.parse_stream_status()
            owner_name = owner.get_name() if owner else "unknown"
            print(f"Stream status de {owner_name}: {status_type.value_name}")
            
        elif mtype == Gst.MessageType.ASYNC_DONE:
            print("Pipeline prêt (ASYNC_DONE)")
            
        elif mtype == Gst.MessageType.NEW_CLOCK:
            clock = message.parse_new_clock()
            print(f"Nouvelle horloge: {clock.get_name()}")
            
        elif mtype == Gst.MessageType.STREAM_START:
            print("Début du stream")
            
        elif mtype == getattr(Gst.MessageType, 'CAPS', None):   # Cette valeur existe bien dans les versions récentes de GStreamer
            # Changement de caps
            element_name = message.src.get_name() if message.src else "unknown"
            print(f"Changement de caps sur {element_name}")
            
        elif mtype == Gst.MessageType.TAG:
            # Tags/métadonnées
            taglist = message.parse_tag()
            element_name = message.src.get_name() if message.src else "unknown"
            print(f"Tags de {element_name}: {taglist.to_string()}")
            
        elif mtype == Gst.MessageType.BUFFERING:
            # Buffering
            percent = message.parse_buffering()
            print(f"Buffering: {percent}%")
            
        return True
    
    def check_files(self):
        """Vérifie l'existence des fichiers"""
        if not Path(self.input_file).exists():
            print(f"Erreur: Fichier d'entrée '{self.input_file}' introuvable")
            return False
            
        # Supprime le fichier de sortie s'il existe
        if Path(self.output_file).exists():
            Path(self.output_file).unlink()
            print(f"Fichier de sortie '{self.output_file}' supprimé")
            
        return True
    
    def check_elements(self):
        """Vérifie la disponibilité des éléments GStreamer"""
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
                # Affichage des informations sur l'élément
                klass = factory.get_klass()
                print(f"✓ {element}: {klass}")
        
        if missing_elements:
            print(f"Éléments manquants: {', '.join(missing_elements)}")
            print("Installez les plugins GStreamer nécessaires")
            return False
            
        return True
    
    def print_element_properties(self, element_name):
        """Affiche les propriétés d'un élément"""
        element = self.elements.get(element_name)
        if not element:
            return
            
        print(f"\nPropriétés de {element_name}:")
        for prop in element.list_properties():
            try:
                value = element.get_property(prop.name)
                print(f"  {prop.name}: {value} ({prop.value_type.name})")
            except:
                print(f"  {prop.name}: (non lisible)")
    
    def run(self):
        """Lance le pipeline"""
        if not self.check_files():
            return False
            
        if not self.check_elements():
            return False
            
        if not self.create_pipeline():
            return False
        
        # Affichage des propriétés (debug)
        if self.debug_level >= "4":
            self.print_element_properties("encoder")
            self.print_element_properties("decoder")
        
        # Configuration du bus
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
        # Démarrage du pipeline
        print("Démarrage du pipeline...")
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Impossible de démarrer le pipeline")
            return False
        elif ret == Gst.StateChangeReturn.ASYNC:
            print("Démarrage asynchrone...")
        
        # Boucle d'événements
        self.loop = GLib.MainLoop()
        self.is_running = True
        
        try:
            print("Pipeline en cours d'exécution... (Ctrl+C pour arrêter)")
            self.loop.run()
        except KeyboardInterrupt:
            print("\nInterruption utilisateur")
            self.stop()
        
        return True
    
    def stop(self):
        """Arrête le pipeline"""
        if self.is_running:
            print("Arrêt du pipeline...")
            self.is_running = False
            
            if self.pipeline:
                self.pipeline.set_state(Gst.State.NULL)
                
            if self.loop:
                self.loop.quit()
    
    def get_progress(self):
        """Affiche le progrès"""
        if self.pipeline and self.is_running:
            try:
                # Requête de position et durée
                success_pos, position = self.pipeline.query_position(Gst.Format.TIME)
                success_dur, duration = self.pipeline.query_duration(Gst.Format.TIME)
                
                if success_pos:
                    pos_sec = position / Gst.SECOND
                    if success_dur and duration > 0:
                        dur_sec = duration / Gst.SECOND
                        progress = (position / duration) * 100
                        print(f"Progrès: {pos_sec:.1f}s / {dur_sec:.1f}s ({progress:.1f}%)")
                    else:
                        print(f"Position: {pos_sec:.1f}s")
            except:
                pass

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre"""
    print("\nSignal reçu, arrêt en cours...")
    sys.exit(0)

def main():
    # Configuration des signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Niveau de debug depuis les arguments
    debug_level = sys.argv[1] if len(sys.argv) > 1 else "3"
    
    print(f"Démarrage avec niveau de debug: {debug_level}")
    
    # Création et lancement du runner
    runner = GstPipelineRunner(debug_level)
    
    # Thread pour afficher le progrès
    def progress_thread():
        while runner.is_running:
            runner.get_progress()
            time.sleep(5)
    
    progress_t = threading.Thread(target=progress_thread, daemon=True)
    progress_t.start()
    
    # Lancement
    success = runner.run()
    
    if success:
        print("Pipeline terminé avec succès")
        if Path(runner.output_file).exists():
            size = Path(runner.output_file).stat().st_size
            print(f"Fichier de sortie créé: {runner.output_file} ({size} octets)")
    else:
        print("Erreur lors de l'exécution du pipeline")
        sys.exit(1)

if __name__ == "__main__":
    main()
