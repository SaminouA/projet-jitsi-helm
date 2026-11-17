
resource "google_container_cluster" "jitsi" {
  name     = "jitsi-cluster"
  location = "europe-west1-b"

  # Les nœuds seront gérés dans un pool séparé
  remove_default_node_pool = true
  initial_node_count       = 1

  # Preuve limitee : label GCP, pas un label de noeud Kubernetes.
  resource_labels = {
    devops-apply-proof = "github-actions"
  }

  # Valeur existante conservee ; aucune modification distante pendant la preparation.
  deletion_protection = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_container_node_pool" "jitsi_nodes" {
  name     = "jitsi-node-pool"
  location = "europe-west1-b"
  cluster  = google_container_cluster.jitsi.name

  node_count = 2

  lifecycle {
    prevent_destroy = true
  }

  node_config {
    machine_type = "e2-standard-2"
    disk_size_gb = 30
    disk_type    = "pd-balanced"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}
