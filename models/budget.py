from odoo import models, fields

class Budget(models.Model):
    _name = "mission.budget"

    name = fields.Integer(string="Imputation budgétaire")