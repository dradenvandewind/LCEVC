
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = "unix:///var/run/docker.sock"
}

 # Build the image from Dockerfile
resource "docker_image" "my_image" {
  name = "myapp:latest"
/*
  build {
    context    = "."
    dockerfile = "Dockerfile"
  }
  */
}
 

# Run the container
resource "docker_container" "my_container" {
  name  = "myapp_container"
  image = docker_image.my_image.image_id

  ports {
    internal = 80
    external = 8080
  }

  command = ["tail", "-f", "/dev/null"]
}
