# The location of this Tiltfile
HERE = os.path.abspath(os.path.dirname(__file__))

# The directory in which the service's values files are located
VALUES_DIR = os.path.join(HERE, "infra", "values")

# Configure the docker build
SERVICE_NAME = "lembas"

# Get the active namespace and make sure it is created
# This can be set with tilt up --namespace <NAMESPACE>
load("ext://namespace", "namespace_create")
namespace = k8s_namespace()
namespace_create(k8s_namespace())

# Build the service image
docker_build(SERVICE_NAME, ".")

# Load environment variables from .env file
load("ext://dotenv", "dotenv")
dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    fail(
      "Must set both `CLIENT_ID` and `CLIENT_SECRET` as environment variables. "
      + "This can be done by placing them in a `.env` file."
    )

# Mount environment variables in a secret
SECRETS_NAME = "secrets"
load("ext://secret", "secret_from_dict")
k8s_yaml(
  secret_from_dict(
    SECRETS_NAME,
    inputs = {
      "CLIENT_ID" : CLIENT_ID,
      "CLIENT_SECRET" : CLIENT_SECRET,
    },
  )
)

# Deploy via Helm chart
load('ext://helm_remote', 'helm_remote')
helm_remote(
  "generic",
  repo_url="https://community-tooling.github.io/charts",
  release_name=SERVICE_NAME,
  namespace=namespace,
  values=[
    os.path.join(VALUES_DIR, "local.yaml"),
  ],
  set=[
    "image.repository={image_name}".format(image_name=SERVICE_NAME),
    "image.tag=local",
  ],
)

# Mark all objects as part of the resource, and rename it to remove "-generic"
k8s_resource(
  "{}-generic".format(SERVICE_NAME),
  new_name=SERVICE_NAME,
  objects=[
    "{}:Namespace".format(namespace),
    "{}-generic:ServiceAccount:{}".format(SERVICE_NAME, namespace),
    "{}-generic:Ingress:{}".format(SERVICE_NAME, namespace),
    "{}:Secret".format(SECRETS_NAME, namespace),
  ],
)
