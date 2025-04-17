FROM python:3.13.2-slim-bookworm AS builder

WORKDIR /

# copy over directory containing ffmpeg, makemkv-oss, and makemkv-bin sources
# hat tip to https://forum.makemkv.com/forum/viewtopic.php?f=3&t=224
COPY ./deps /deps

# install other build dependencies
RUN sed -i 's/main/main non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
  build-essential \
  pkg-config \
  libc6-dev \
  libssl-dev \
  libexpat1-dev \
  libavcodec-dev \
  libgl1-mesa-dev \
  qtbase5-dev \
  zlib1g-dev \
  nasm \
  libfdk-aac-dev \
  less \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*


# configure and build ffmpeg from source so I can link in up-to-date versions of its
# encoders when building makemkv
RUN cd /deps/ffmpeg \
  && ./configure \
  --prefix=/tmp/ffmpeg \
  --enable-static \
  --disable-shared \
  --enable-pic \
  --enable-libfdk-aac \
  && make install

# build makemkv-oss first
RUN cd /deps/makemkv-oss \
  && PKG_CONFIG_PATH=/tmp/ffmpeg/lib/pkgconfig ./configure \
  && make \
  && make install

# then we can build makemkv-bin
RUN cd /deps/makemkv-bin && make && make install

# a lil terrarium for the python
WORKDIR /app
RUN pip install poetry
# COPY ./app/poetry.lock /app/poetry.lock
# COPY ./app/pyproject.toml /app/pyproject.toml

# to use the `poetry run ripper` script shortcut, I need poetry to install the source as a
# project; and to do that, its source code must be copied into the container before
# running `poetry install`.
COPY ./app /app
RUN poetry install

### NOTE: everything above this point is tested and works (i.e. installs `makemkvcon`)
### NOTE: nothing below this point is tested

# expose port
EXPOSE 8888

# once a web server wrapper exists, start it up here
# CMD ["poetry", "run", "python", "main.py"]
