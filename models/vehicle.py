from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Vehicle(models.Model):
    _name = "mission.vehicle"
    _description = "Voiture de services"

    voiture_id = fields.Many2one("fleet.vehicle", string="Voiture")
    conducteur = fields.Many2one("res.partner", string="Conducteur", store=True)
    mission_id = fields.Many2one("mission.delegation", string="Mission")

    def name_get(self):
        vehicle = []
        for record in self:
            rec_name = "%s" % (record.voiture_id.name)
            vehicle.append((record.id, rec_name))
        return vehicle

    # @api.onchange("voiture_id")
    # def _onchange_conducteur(self):
    #     for record in self:
    #         if record.voiture_id:
    #             record.conducteur = record.voiture_id.driver_id.name
