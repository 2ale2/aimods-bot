FROM python:3.12.3

WORKDIR /app

RUN apt-get update && \
    apt-get install -y locales texlive-luatex texlive-latex-recommended texlive-fonts-recommended fonts-noto-color-emoji texlive-latex-extra texlive-lang-italian && \
    sed -i '/it_IT.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen it_IT.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=it_IT.UTF-8
ENV LANGUAGE=it_IT:it
ENV LC_ALL=it_IT.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH="${PYTHONPATH}:/app"

ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

CMD ["python", "aimods_bot/src/main/init.py"]