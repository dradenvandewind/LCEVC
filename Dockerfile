FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

# Env vars
#ENV PYTHONPATH=/usr/local/lib/python3.8/site-packages:/usr/local/lib/python3.10/site-packages:/usr/local/lib/python3.11/site-packages:/usr/lib/python3.10

ENV GI_TYPELIB_PATH=/usr/local/lib/x86_64-linux-gnu/girepository-1.0:/usr/lib/x86_64-linux-gnu/girepository-1.0
ENV GST_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/gstreamer-1.0/
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV DISPLAY=:1
ENV GST_DEBUG=2
ENV GST_DEBUG_DUMP_DOT_DIR=/tmp
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/cuda/lib64/
ENV TF_FORCE_GPU_ALLOW_GROWTH=true
ENV TF_ENABLE_GPU_GARBAGE_COLLECTION=false
ENV PREFIX=/usr
ENV TAG=1.26.2
ENV TAGLCEVC=3.3.6
ENV TZ=Europe/Paris

# Timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# Installer les outils nécessaires pour gérer les dépôts
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common

RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get install -y --no-install-recommends pkg-config \
nlohmann-json3-dev \
libfmt-dev \
libcli11-dev \ 
libavcodec-dev \
libavformat-dev \
libavutil-dev \
libavfilter-dev \
libgtest-dev \
libgmock-dev \
libxxhash-dev \
librange-v3-dev \
git \
build-essential \
cmake \
ninja-build \
python3.9 \
python3-pip \
python3-setuptools \
python3-distutils

WORKDIR /root/workingsrc
#PATCH mpegtsmux transport stream
RUN git clone https://github.com/v-novaltd/LCEVCdec.git && \
cd LCEVCdec && \
git checkout tags/$TAGLCEVC && \
mkdir build && \
cd build && \
cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DVN_SDK_EXECUTABLES=ON -DVN_SDK_UNIT_TESTS=ON -DCMAKE_BUILD_TYPE=Release -G Ninja && \
cmake --build . --config Release && \
cmake --install . && \
ldconfig 

# build gstreamer section

RUN apt-get update && apt-get install -y --no-install-recommends  flex bison \
    gobject-introspection \
    libgirepository1.0-dev \
    vim \
    nano \
    net-tools \
    tcpdump \
    alsa-utils \
    lshw \
    graphviz \
    syslog-ng \
    openssh-client \
    python3-dev \
    libpython3-dev \
    python3-dev \
    meson ninja-build git \
    libglib2.0-dev libgirepository1.0-dev gobject-introspection \
    libffi-dev libtool pkg-config curl wget libxml2-dev autogen automake nasm



RUN echo "Fetching x264..." && \
git clone https://github.com/mirror/x264.git && \
cd x264 && \
echo "Building x264..." && \
./configure --prefix=/usr/local --enable-pic --enable-shared && make && make install

RUN apt update && \
apt install -y build-essential cmake git nasm yasm mercurial libnuma-dev cmake-curses-gui cmake   
RUN echo "Building x265..." && \
git clone https://bitbucket.org/multicoreware/x265_git.git && \
cd x265_git/source && \
mkdir -p build && \
cd build && \
cmake .. \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DENABLE_SHARED=ON \
        -DENABLE_CLI=ON \
        -DENABLE_PIC=ON \
        -DENABLE_ASSEMBLY=ON && \
make -j$(nproc) && \
make install && ldconfig

RUN pip install "setuptools<65" meson==1.4.0
RUN apt-get install -y libc6-dev 
RUN git clone https://gitlab.freedesktop.org/gstreamer/gstreamer.git && \
  cd gstreamer && \
  git checkout tags/$TAG && \
  mkdir build && cd build && \
  meson setup ..            \
       -Dgpl=enabled -Dugly=enabled -Dgst-plugins-ugly:x264=enabled \
       -Dgst-plugins-bad:x265=enabled -Dbad=enabled \
       -Dgst-plugins-bad:lcevcdecoder=enabled \
       --prefix=/usr       \
       --buildtype=release && \
  ninja && \
  ninja install && \
  ldconfig 
#raw souce https://media.xiph.org/video/derf/
RUN wget https://media.xiph.org/video/derf/y4m/akiyo_cif.y4m 


#add lcvec encoder
RUN git clone https://github.com/mpeg5/xeve && \
cd xeve && \
mkdir build && \
cd build && \
cmake .. && \
make && \
make install && \
ldconfig

#xeve_app -i akiyo_cif.y4m -w 352 -h 288 -z 30 -o xeve.evc
ENV PKG_CONFIG_PATH=/usr/lib/pkgconfig:$PKG_CONFIG_PATH

COPY *.sh /root/workingsrc/
COPY *.evc /root/workingsrc/
COPY *py /root/workingsrc/

RUN git clone https://github.com/mpeg5/xevd.git && \
cd xevd && \
mkdir build && \
cd build && \
cmake .. && \
make && \
make install && \
ldconfig
#xevd_app -i akyio.evc -o akyio_lcvev.yuv
#

RUN git clone https://github.com/fraunhoferhhi/vvenc.git vvenc-1.4.0 && \
cd vvenc-1.4.0 && \
git checkout tags/v1.4.0 && \
mkdir build && \
cd build && \
cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON && \
make && \
make install && \
ldconfig && cd ../..



COPY ./gst_pipeline*.py /root/workingsrc/
COPY ../ts_start_end_to_end.sh /root/workingsrc/
COPY ../test_h266_10_bit.sh /root/workingsrc/

COPY ./lib4lcevc /root/workingsrc/
RUN cp *.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0/ && ldconfig
RUN cp libvvenc_lib.so /usr/lib/x86_64-linux-gnu/libvvenc_lib.so && ldconfig 

RUN export GST_DEBUG_DUMP_DOT_DIR=/tmp/

ARG USER_ID=1000
ARG GROUP_ID=1000
ARG USERNAME=user

RUN groupadd -g $GROUP_ID $USERNAME && \
    useradd -u $USER_ID -g $GROUP_ID -m -s /bin/bash $USERNAME

RUN usermod -aG video,audio $USERNAME
RUN groupadd -g 109 render
#getent group render

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
CMD gst-inspect-1.0 --version || exit 1


CMD ["/bin/bash"]
