FROM centos:7
MAINTAINER daniel.vrcic@gmail.com
RUN groupadd user -g 1000 && useradd -u 1000 -g 1000 user -m -d /home/user -s /bin/zsh
RUN yum -y update; yum clean all
RUN yum -y install epel-release && \
    yum -y install \
      ack \
      ctags \
      fortune-mod \
      git \
      iproute \
      make \
      mc \
      net-tools \
      python-devel \
      python-pip \
      python-setuptools \
      python3-devel \
      python3-setuptools \
      rpmdevtools \
      sshd \
      sudo \
      the_silver_searcher \
      tmux \
      vim \
      wget \
      yum-utils \
      zsh
RUN rpm --import https://www.elrepo.org/RPM-GPG-KEY-elrepo.org && \
    yum install -y https://www.elrepo.org/elrepo-release-7.el7.elrepo.noarch.rpm
RUN pip install -U pip; pip3 install -U pip
RUN pip2 install wheel ipdb setuptools; pip3 install -U wheel ipdb setuptools
COPY galapix-0.1.3-1.el7.x86_64.rpm /home/user
COPY amdgpu-install-21.50.50000-1.el7.noarch.rpm /home/user
RUN yum localinstall -y /home/user/galapix-0.1.3-1.el7.x86_64.rpm && \
    yum install -y mesa-dri-drivers && \
		yum localinstall -y /home/user/amdgpu-install-21.50.50000-1.el7.noarch.rpm && \
		yum install -y 'nvidia-x11-drv-5*'
RUN /usr/bin/amdgpu-install -y
RUN passwd -d root
RUN echo "user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
RUN echo "Defaults env_keep += \"PYTHONPATH\"" >> /etc/sudoers
RUN ln -s /home/user /home/daniel; ln -s /home/user /home/dvrcic
USER user
WORKDIR /home/user
RUN curl -sfL https://git.io/chezmoi | sh
CMD ["/bin/zsh"]
