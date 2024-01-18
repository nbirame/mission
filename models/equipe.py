from odoo import fields, models, api


class Equipe(models.Model):
    _name = "mission.equipe"
    _description = "Equipe de Mission"

    employee_id = fields.Many2one("hr.employee", required=True, string="Employée")
    poste = fields.Char(string="Titre poste", compute="_compute_poste", store=True)
    type_missionnaire_id = fields.Many2one("mission.missionnaire", string="Type de Missionnaire", required=True)
    indemnite = fields.Integer(string="Indemnité journalière", compute="_compute_indemnite", store=True)
    # indemnite_id = fields.Many2one("mission.indemnite", string="Indemnité journalière")
    prise_en_charge = fields.Selection([
        ('Carburant', 'Carburant'), ('Perdieme', 'Perdieme'), ('Carburant/Perdieme', 'Carburant/Perdieme'),
    ], 'Prise en Charge', default="Carburant")
    avance = fields.Integer(string="Montant avancé", compute="_compute_avance", store=True)
    restant = fields.Integer(string="Montant restant", compute="_compute_restant", store=True)
    total = fields.Integer(string="Montant Total", compute="_compute_total", store=True)
    contrat = fields.Binary(string="Joindre OM signé")
    mission_id = fields.Many2one('mission.delegation', string="Mission")
    ordre_mission = fields.Binary(string="Ordre de la Mission", store=True)
    ordre_mission_name = fields.Char(string="OM Signé", store=True)

    def name_get(self):
        eq = []
        for record in self:
            rec_name = "%s" % (record.employee_id.name)
            eq.append((record.id, rec_name))
        return eq

    @api.depends("mission_id", "type_missionnaire_id")
    def _compute_indemnite(self):
        for record in self:
            if record.type_missionnaire_id:
                indemnite = self.env['mission.indemnite'].sudo().search(
                    [('missionnaire_id', '=', record.type_missionnaire_id.id),
                     ('zone_id', '=', record.mission_id.zone_id.id),
                     ('type_mission_id', '=', record.mission_id.type_mission_id.id)
                     ], limit=1)
                if indemnite:
                    record.indemnite = indemnite.montant
                else:
                    indemnite = self.env['mission.indemnite'].sudo().search(
                        [
                            ('type_mission_id', '=', record.mission_id.type_mission_id.id)
                        ], limit=1)
                    record.indemnite = indemnite.montant

    @api.depends("employee_id")
    def _compute_poste(self):
        for record in self:
            record.poste = record.employee_id.job_title

    # Le montant total de l'indemnité est calculer en fonction du nombre de nuité et de l'indemnité journalière
    @api.depends("mission_id", "type_missionnaire_id")
    def _compute_total(self):
        for record in self:
            record.total = record.mission_id.nb_nuit * record.indemnite

    @api.depends("total", "mission_id", "type_missionnaire_id")
    def _compute_avance(self):
        for record in self:
            # if record.mission_id.type_mission_id.type_miss == "interieur" or record.mission_id.type_mission_id.type_miss == "Interieur" or record.mission_id.type_mission_id.type_miss == "intérieur" or record.mission_id.type_mission_id.type_miss == "Intérieur":
            if record.mission_id.type_mission_id.type_miss == "Interieur":
                # Pour une mission interne est l'avance est de 2/3 et les 1/3 restant payé au retour
                record.avance = (record.total * 2) / 3
            else:
                # Pour une mission externe est l'avance est de 3/4 et les 1/4 restant payé au retour
                record.avance = (record.total * 4) / 5

    @api.depends('total', "type_missionnaire_id")
    def _compute_restant(self):
        for record in self:
            # if record.mission_id.nb_nuit or record.mission_id.type_mission_id.indemnite:
            record.restant = record.total - record.avance

    # methode qui permet d'imprimer le report de l'equipe de mission
    def report_print(self):
        return self.env.ref("mission.report_mission_agent").report_action(self)

    def somme_avance(self):
        somme = []
        mission = self.env['mission.equipe'].sudo().search([('mission_id', '=', self.mission_id.id)])
        for avance in mission:
            somme.append(avance.avance)
        print(somme)
        return somme
