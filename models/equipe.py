from odoo import fields, models, api

class Equipe(models.Model):
    _name = "mission.equipe"
    _description = "Equipe de Mission"

    employee_id = fields.Many2one("hr.employee", required=True, string="Employée")
    poste = fields.Char(string="Titre poste", compute="_compute_poste", store=True)
    type_missionnaire_id = fields.Many2one("mission.missionnaire", string="Type de Missionnaire", required=True)
    indemnite = fields.Integer(string="Indemnité journalière", store=True)
    prise_en_charge = fields.Selection([
        ('Carburant', 'Carburant'),
        ('Perdieme', 'Perdieme'),
        ('Carburant/Perdieme', 'Carburant/Perdieme'),
    ], 'Prise en Charge', default="Carburant")
    avance = fields.Integer(string="Montant avancé", store=True)
    restant = fields.Integer(string="Montant restant", store=True)
    total = fields.Integer(string="Montant Total", store=True)
    contrat = fields.Binary(string="Joindre OM signé")
    mission_id = fields.Many2one('mission.delegation', string="Mission")
    ordre_mission = fields.Binary(string="Ordre de la Mission", store=True)
    ordre_mission_name = fields.Char(string="OM Signé", store=True)

    def name_get(self):
        """
        Affiche le nom de l'employé dans les listes déroulantes.
        """
        eq = []
        for record in self:
            rec_name = "%s" % (record.employee_id.name)
            eq.append((record.id, rec_name))
        return eq

    @api.onchange("mission_id", "type_missionnaire_id", "prise_en_charge")
    def _onchange_indemnite(self):
        """
        Calcule l'indemnité journalière selon:
        - Le type de missionnaire
        - La zone (si applicable)
        - Le type de mission (ex: Interne ou Externe)
        - La prise en charge (si != "Carburant")
        """
        for record in self:
            if not record.mission_id or not record.type_missionnaire_id:
                # Si pas de mission ou pas de type missionnaire, on remet l'indemnité à zéro.
                record.indemnite = 0
                continue

            if record.prise_en_charge != "Carburant":
                indemnite_obj = self.env['mission.indemnite'].sudo()
                # Premier search: on essaie zone + missionnaire + type_mission
                indemnite = indemnite_obj.search([
                    ('missionnaire_id', '=', record.type_missionnaire_id.id),
                    ('zone_id', '=', record.mission_id.zone_id.id),
                    ('type_mission_id', '=', record.mission_id.type_mission_id.id)
                ], limit=1)

                # S'il n'y a pas de correspondance, on refait un search plus global
                if not indemnite:
                    indemnite = indemnite_obj.search([
                        ('type_mission_id', '=', record.mission_id.type_mission_id.id)
                    ], limit=1)

                # On assigne
                record.indemnite = indemnite.montant if indemnite else 0
            else:
                record.indemnite = 0

    @api.depends("employee_id")
    def _compute_poste(self):
        """
        Récupère le titre de poste depuis la fiche employé.
        """
        for record in self:
            record.poste = record.employee_id.job_title

    @api.onchange("mission_id", "type_missionnaire_id", "prise_en_charge")
    def _onchange_total(self):
        """
        Calcule le montant total en fonction:
        - Du nombre de nuits (mission_id.nb_nuit)
        - De l'indemnité journalière
        - De la prise en charge
        """
        for record in self:
            if record.mission_id and record.prise_en_charge != "Carburant":
                record.total = record.mission_id.nb_nuit * record.indemnite
            else:
                record.total = 0

    @api.onchange("total", "mission_id", "prise_en_charge")
    def _onchange_avance(self):
        """
        Calcule l'avance: si mission extérieure => 4/5, sinon => 2/3.
        """
        for record in self:
            if not record.mission_id:
                record.avance = 0
                continue

            # Normalise en minuscule et compare
            type_miss_lower = record.mission_id.type_mission_id.type_miss.lower()
            is_externe = any(x in type_miss_lower for x in ['exterieur', 'externe', 'extérieure'])

            if is_externe:
                record.avance = (record.total * 4) / 5
            else:
                record.avance = (record.total * 2) / 3

    @api.onchange('total', "type_missionnaire_id", "prise_en_charge")
    def _onchange_restant(self):
        """
        Calcule le restant dû = total - avance, si prise_en_charge != "Carburant".
        """
        for record in self:
            if record.prise_en_charge != "Carburant":
                record.restant = record.total - record.avance
            else:
                record.restant = 0

    def report_print(self):
        """
        Méthode pour imprimer le report de l'équipe.
        """
        return self.env.ref("mission.report_mission_agent").report_action(self)

    def somme_avance(self):
        """
        Additionne les avances de tous les membres de l'équipe associés à la même mission.
        """
        somme = []
        mission = self.env['mission.equipe'].sudo().search([('mission_id', '=', self.mission_id.id)])
        for avance in mission:
            somme.append(avance.avance)
        return somme

    def get_imputation_bugetaire(self):
        """
        Récupère le dernier budget créé.
        """
        budgets = self.env['mission.budget'].sudo().search([])
        return budgets[-1].name if budgets else ""
