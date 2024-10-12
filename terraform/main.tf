resource "juju_model" "postgresql" {
  count = var.create_model ? 1 : 0
  name  = var.model_name
}
