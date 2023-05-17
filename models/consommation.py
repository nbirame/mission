from odoo import models, fields, api


class Consommation(models.Model):
    _description = "Consommation Carburant"
    _inherit = "carburant.consommation"

    # nb_littre = fields.Float(string="Nombre de littres", compute="_compute_nb_littre", store=True)
    delegation_id = fields.Many2one("mission.delegation", string="Mission")

    # @api.depends("delegation_id")
    # def _compute_nb_littre(self):
    #     for record in self:
    #         if record.delegation_id.carburant:
    #             record.nb_littre = record.delegation_id.carburant

    # prix = fields.Float(string="Prix", compute="_compute_prix", store=True)
    # total = fields.Float(string="Total", compute="_compute_total", store=True)
    # vehicule_id = fields.Many2one("fleet.vehicle", string="Véhicule")
    # delegation_id = fields.Many2one("mission.delegation", string="Mission")
    # carte_id = fields.Many2one("mission.cartecarburant", string="Carte")
    #
    # @api.depends("nb_littre", "prix")
    # def _compute_total(self):
    #     for record in self:
    #         if record.nb_littre or record.prix:
    #             record.total = record.nb_littre * record.prix
    #
    # @api.depends("delegation_id")
    # def _compute_nb_littre(self):
    #     for record in self:
    #         if record.delegation_id.carburant:
    #             record.nb_littre = record.delegation_id.carburant
    #
    # @api.depends("delegation_id")
    # def _compute_prix(self):
    #     for record in self:
    #         record.prix = record.delegation_id.prix_littre




















