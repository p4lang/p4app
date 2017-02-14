FROM p4lang/p4c:latest
MAINTAINER Seth Fowler <seth@barefootnetworks.com>
MAINTAINER Robert Soule <robert.soule@barefootnetworks.com>

# Install dependencies and some useful tools.
ENV NET_TOOLS net-tools nmap tshark
ENV MININET_DEPS cgroup-bin \
                 ethtool \
                 gcc \
                 help2man \
                 iperf \
                 iproute \
                 make \
                 psmisc \
                 socat \
                 ssh \
                 telnet \
                 pep8 \
                 pyflakes \
                 pylint \
                 python-pexpect \
                 python-setuptools
RUN apt-get update && \
    apt-get install -y --no-install-recommends $NET_TOOLS $MININET_DEPS

# Install mininet.
COPY docker/third-party/mininet /third-party/mininet
WORKDIR /third-party/mininet
RUN make install && \
    rm -rf /third-party/mininet

# Install p4c system-wide.
WORKDIR /p4c/build
RUN make install

# Create a volume to hold log files. This is a workaround for the old version of
# coreutils included in Ubuntu 14.04, which contains a version of tail that
# doesn't interact well with overlayfs.
VOLUME /var/log

# Install the scripts we use to run and test P4 apps.
COPY docker/scripts /scripts
WORKDIR /scripts

ENTRYPOINT ["./p4apprunner.py"]
