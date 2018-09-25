FROM p4lang/p4c:latest
MAINTAINER Seth Fowler <seth@barefootnetworks.com>
MAINTAINER Theo Jepsen <jepset@usi.ch>
MAINTAINER Robert Soule <robert.soule@barefootnetworks.com>

# Install dependencies and some useful tools.
ENV NET_TOOLS iputils-arping \
              iputils-ping \
              iputils-tracepath \
              net-tools \
              nmap \
              python-ipaddr \
              python-scapy \
              python-psutil \
              python-pip \
              tcpdump \
              traceroute \
              tshark
ENV MININET_DEPS automake \
                 build-essential \
                 cgroup-bin \
                 ethtool \
                 gcc \
                 help2man \
                 iperf \
                 iproute \
                 libtool \
                 make \
                 pkg-config \
                 psmisc \
                 socat \
                 ssh \
                 sudo \
                 telnet \
                 pep8 \
                 pyflakes \
                 pylint \
                 python-pexpect \
                 python-setuptools

# Ignore questions when installing with apt-get:
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends $NET_TOOLS $MININET_DEPS

# Fix to get tcpdump working
RUN mv /usr/sbin/tcpdump /usr/bin/tcpdump

# Upgrade gRPC python bindings
RUN pip install --upgrade grpcio

# Install mininet.
COPY docker/third-party/mininet /third-party/mininet
WORKDIR /third-party/mininet
RUN cp util/m /usr/local/bin/m
RUN make install && \
    rm -rf /third-party/mininet

# Install the scripts we use to run and test P4 apps.
COPY docker/scripts /scripts
RUN mkdir /p4app
WORKDIR /p4app

ENV PYTHONPATH "/scripts:${PYTHONPATH}"
ENV DISPLAY ":0"

ENTRYPOINT ["/scripts/p4apprunner.py"]
