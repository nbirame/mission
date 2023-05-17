from odoo import fields, models, api, _


class Agent(models.Model):
    _description = "Agent"
    _inherit = "hr.employee"
    _order = 'id desc'

    equipe_is = fields.One2many("mission.equipe", "employee_id", string="Equipe")
    state = fields.Selection([
        ('en_mission', 'en_mission'),
        ('disponible', 'disponile')
    ], "Etat", default="disponible")
    number_mission_participation = fields.Integer(string="Nombre de Deplacement", compute="_compute_number_mission_participation", store=True)

    def return_action_to_open(self):
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:

            res = self.env['ir.actions.act_window']._for_xml_id('mission.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_employee_id=self.id, group_by=False),
                domain=[('employee_id', '=', self.id)]
            )
            return res
        return False

    @api.depends("equipe_is")
    def _compute_number_mission_participation(self):
        for record in self:
            record.number_mission_participation = len(record.equipe_is)