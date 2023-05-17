from odoo import fields, models


class Odometre(models.Model):
    _description = "Kilometrage"
    _inherit = "fleet.vehicle.odometer"

    conducteur_id = fields.Many2one("res.partner", string="Chauffeur")
    # suivi_id = fields.Many2one("mission.suivi_essence", string="Suivi")