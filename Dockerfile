FROM --platform=linux/amd64 continuumio/miniconda3:24.5.0-0@sha256:0fe3d011c129245af1f631d19c6b7c4f34b61650c1c7881980f266cdaa44ed1b as builder

# TODO: Replace this with a new builder image that is generated from its own lockfile
RUN conda install -c conda-forge --override-channels conda-project

WORKDIR /app

# Pre-install project dependencies during image build
COPY ./conda-lock.prod.yml ./
#COPY ./conda-project.yml ./
#COPY ./environment-*.yml ./

# Create the prod conda environment
RUN conda lock install -p /opt/env conda-lock.prod.yml
ENV PATH="/opt/env/bin:${PATH}"

# Because conda project is re-locking each time, I'm using conda-lock for now
#RUN conda project install --environment prod

# Copy in the app code
COPY static/ ./static
COPY videos/ ./videos
COPY templates/ ./templates
COPY main.py ./

# Expose the port and run the service
EXPOSE 8000
ENTRYPOINT ["fastapi"]
CMD ["run", "main.py"]

# Once we fix conda project, we may want to consider using this instead
#ENTRYPOINT ["conda", "project", "run"]
#CMD ["prod"]
