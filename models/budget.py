from odoo import models, fields

class Budget(models.Model):
    _name = "mission.budget"
    _description = "Imputation bugetaire"

    name = fields.Integer(string="Imputation budgétaire")