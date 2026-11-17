# Bucket preexistant et migration de l'etat obligatoires avant activation CI.
# Aucun bucket cree par cette configuration ; pas de credentials versionnes.
terraform {
  backend "gcs" {}
}
