from odoo import fields, models, api


class Type(models.Model):
    _name = "mission.type_mission"
    _description = "Type de Mission "

    type_miss = fields.Char(string="Type de mission")
    indemnite_ids = fields.One2many("mission.indemnite", "type_mission_id", string="Indemnité", store=True)
    # indemnite = fields.Integer(string="Montant indemnité journalière", default="25000", compute="_compute_indemnite", store=True)
    # zone_mission_ids = fields.One2many("mission.zone", "type_id", string="Zone de Mission")
    #
    # @api.depends("zone_mission_ids")
    # def _compute_indemnite(self):
    #     for record in self:
    #         for zone in record.zone_mission_ids.ids:
    #             record.indemnite = zone.indemnite_journaliere
    _sql_constraints = [
        ('type_miss_uniq', 'unique (type_miss)', 'Le type de mission doit etre unique')
    ]

    def name_get(self):
        ty = []
        for record in self:
            rec_name = "%s" % (record.type_miss)
            ty.append((record.id, rec_name))
        return ty
