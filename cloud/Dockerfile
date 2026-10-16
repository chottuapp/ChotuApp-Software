FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8080 CHOTUAPP_CLOUD_DATA=/data CHOTUAPP_AUTO_CONTINUE=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-tk ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt playwright==1.55.0 && /opt/venv/bin/python -m playwright install --with-deps chromium && chmod -R a+rX /opt/browsers
COPY main.py seran_source_support.py resume_support.py parallel_store_support.py store_process_worker.py software_revision_support.py fast_fetch_support.py farda_source_support.py complete_description_support.py czone_source_support.py install_fast_fetch.py install_farda_source.py install_czone_source.py install_speed_patch.py remove_daily_auto.py /app/
COPY importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx /app/importer-files/Chotu_Products_Import_Template_Discount_Tags.xlsx
COPY cloud /app/cloud
RUN useradd --uid 10001 --create-home chotu && mkdir /data && chown chotu:chotu /data
USER chotu
VOLUME /data
EXPOSE 8080
CMD ["/opt/venv/bin/python", "cloud/server.py"]
