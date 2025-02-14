# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from math import ceil
from num2words import num2words
import calendar


class Delegation(models.Model):
    _name = 'mission.delegation'
    _description = 'Délégué de Mission'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Numéro de mission", readonly=True, store=True)
    type_mission_id = fields.Many2one("mission.type_mission", string="Type de mission")
    zone_id = fields.Many2one("mission.zone", string="Zone")
    motif = fields.Text(string="Motifs", required=True)
    lettre = fields.Binary(string="Lettre de mission")
    chef = fields.Many2one("hr.employee", string="Chef de mission", required=True)
    trajet = fields.Char(string="Trajet", required=True)
    moyen_transport = fields.Selection([
        ('Voiture', 'Voiture'),
        ('Avion', 'Avion'),
        ('Bateau', 'Bateau'),
        ('Train', 'Train'),
    ], 'Moyen de Transport', default='Voiture')
    date_depart = fields.Date(string="Date de départ", required=True, default=fields.Date.today, tracking=True)
    date_retour = fields.Date(string="Date de retour", required=True, tracking=True)
    lieu_depart = fields.Many2one("mission.adresse", string="Lieu de départ", required=True)
    lieu_arrive = fields.Many2one("mission.adresse", string="Lieu d'arrivée", required=True)
    distance = fields.Integer(string="Distance aller-retour en KM", compute="_compute_distance", store=True)
    duree = fields.Integer(string="Durée", compute="_compute_duree", store=True)
    nb_nuit = fields.Integer(string="Nombre de nuit", compute="_compute_nb_nuit", store=True)
    carburant = fields.Float(string="Nombre de littres carburant nécessaire", store=True)
    observation = fields.Text(string="Observation")
    total_perdieme = fields.Integer(string="Total perdieme", compute="_compute_total_perdieme", store=True)
    cout_mission = fields.Integer(string="Cout de la mission", compute="_depends_cout_mission", store=True)
    equipe_id = fields.One2many("mission.equipe", "mission_id", string="Equipe de la mission", store=True)
    vehicule_id = fields.One2many("mission.vehicle", "mission_id", string="Les Véhicule de la mission", store=True)
    consommation_id = fields.One2many("carburant.consommation", "delegation_id", string="Consomation", store=True)
    source = fields.Selection([('Cart', 'Carte'), ('Ticket', 'Ticket')], 'Source', default="Cart")
    nombre_ticket = fields.Integer(string="Nombre de tickets", store=True)
    prix_littre = fields.Float(string="Prix en (FCFA)", store=True)
    cout_ticket = fields.Float(string="Cout Tickets", store=True)
    cout_carburant = fields.Float(string="Cout du carburant", compute="_compute_cout_carburant", store=True)
    dotation_carburant = fields.Float(string="Dotation carburant", compute="_compute_dotation_carburant", store=True)
    cartecarburant_id = fields.Many2one("carburant.cartecarburant", string="Choisir la carte de carburant")
    state = fields.Selection([
        ('programmer', 'Brouillon'),
        ('confirmer', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminer', 'Terminée'),
        ('annuler', 'Annulée'),
    ], default='programmer', store=True, string="Status")
    rapport_mission = fields.Binary(string="Rapport de la Mission")
    rapport_mission_name = fields.Char(string="Rapport de la Mission", store=True)

    # -------------------------------------------------------------------------
    #                   CONTRAINTES ET VERIFICATIONS
    # -------------------------------------------------------------------------

    @api.constrains("chef", "date_depart", "date_retour")
    def _check_chef(self):
        """
        Vérifie que le chef ne soit pas déjà en mission sur une période qui se chevauche
        et qu'il n'est pas en état "en_mission" pour la même période.
        """
        for record in self:
            if record.date_depart and record.date_retour and record.chef:
                # On exclut la mission courante
                domain = [
                    ('id', '!=', record.id),
                    ('chef', '=', record.chef.id),
                    # On regarde si les dates se chevauchent
                    ('date_depart', '<=', record.date_retour),
                    ('date_retour', '>=', record.date_depart),
                ]
                missions = self.env["mission.delegation"].sudo().search(domain)
                for mission in missions:
                    # Si le chef est déjà marqué "en_mission" dans l'autre mission
                    if mission.chef and mission.chef.state == "en_mission":
                        raise ValidationError(_(
                            "Le chef de mission doit être en mission pendant cette période : %s"
                        ) % mission.name)

    @api.model
    def get_month_start(self):
        """Retourne la date de début du mois courant."""
        today = fields.Date.today()
        return today.replace(day=1)

    @api.model
    def get_month_end(self):
        """Retourne la date de fin du mois courant."""
        from calendar import monthrange
        today = fields.Date.today()
        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=last_day)

    @api.constrains('equipe_id', 'date_depart', 'date_retour')
    def _check_equipe_id(self):
        """
        1) Vérifie que la date de retour >= date de départ.
        2) Calcule le nombre de jours de la mission.
        3) Vérifie, pour chaque membre, s'il ne dépasse pas 10 jours de mission ce mois-ci.
        """
        for mission in self:
            if mission.date_depart and mission.date_retour:
                # 1) Vérif cohérence des dates
                if mission.date_retour < mission.date_depart:
                    raise ValidationError(
                        _("La date de retour doit être supérieure ou égale à la date de départ.")
                    )

                # 2) Nombre de jours de la nouvelle mission
                new_mission_days = (mission.date_retour - mission.date_depart).days + 1

                # 3) On cherche les missions du mois courant qui se superposent
                domain_month = [
                    ('id', '!=', mission.id),
                    ('date_depart', '<=', mission.get_month_end()),
                    ('date_retour', '>=', mission.get_month_start()),
                ]
                month_missions = self.env['mission.delegation'].sudo().search(domain_month)

                # 4) Pour chaque membre, on cumule ses jours déjà pris
                for membre in mission.equipe_id:
                    eq_missions = self.env['mission.equipe'].sudo().search([
                        ('employee_id', '=', membre.employee_id.id),
                        ('mission_id', 'in', month_missions.ids),
                    ])
                    total_days_for_membre = 0
                    for eq in eq_missions:
                        if eq.mission_id.date_depart and eq.mission_id.date_retour:
                            total_days_for_membre += (eq.mission_id.date_retour - eq.mission_id.date_depart).days + 1

                    # 5) Vérification
                    if total_days_for_membre + new_mission_days > 10:
                        raise ValidationError(_(
                            "Le membre %(membre)s dépasse le quota de 10 jours de mission pour ce mois. "
                            "Il a déjà fait %(nombre)s jours",
                            membre=membre.employee_id.name,
                            nombre=total_days_for_membre
                        ))

    @api.constrains("cartecarburant_id", "carburant")
    def _check_cartecarburant_id(self):
        """
        Vérifie que la carte sélectionnée dispose bien du nombre de litres disponibles
        pour couvrir la mission (carburant).
        """
        for rec in self:
            if rec.cartecarburant_id and rec.carburant:
                if rec.cartecarburant_id.restant_littre < rec.carburant:
                    raise ValidationError(_(
                        "La carte %s ne contient pas le nombre de litres nécessaire pour le voyage."
                    ) % rec.cartecarburant_id.name)

    # -------------------------------------------------------------------------
    #                   CALCULS ET CHAMPS COMPUTE
    # -------------------------------------------------------------------------

    @api.depends("lieu_arrive")
    def _compute_distance(self):
        """
        Calcule la distance aller-retour depuis le champ "distance" du lieu d'arrivée.
        """
        for record in self:
            record.distance = 0
            if record.lieu_arrive and record.lieu_arrive.distance:
                record.distance = record.lieu_arrive.distance * 2

    @api.depends("date_depart", "date_retour")
    def _compute_duree(self):
        """
        Calcule le nombre de jours à partir de la date de départ et de la date de retour.
        """
        for record in self:
            record.duree = 0
            if record.date_depart and record.date_retour:
                diff_jours = (record.date_retour - record.date_depart).days
                if diff_jours < 0:
                    raise ValidationError(_("La date de retour ne doit pas être antérieure à la date de départ."))

                # +1 car si départ=retour, ça fait 1 jour
                nombre_jours = diff_jours + 1
                if nombre_jours > 10:
                    raise ValidationError(_("Le nombre de jours de mission ne doit pas dépasser 10 jours."))
                record.duree = nombre_jours

    @api.depends("duree")
    def _compute_nb_nuit(self):
        """
        Calcule le nombre de nuits (duree - 1).
        """
        for record in self:
            record.nb_nuit = 0
            if record.duree:
                record.nb_nuit = record.duree - 1

    @api.depends('equipe_id')
    def _compute_total_perdieme(self):
        """
        Somme du total de perdieme sur chaque ligne de l'équipe.
        """
        for record in self:
            total_p = sum(equipe.total for equipe in record.equipe_id)
            record.total_perdieme = total_p

    @api.depends("vehicule_id", "carburant")
    def _compute_dotation_carburant(self):
        """
        Dotation carburant = nombre de véhicules * nombre de litres prévu.
        """
        for record in self:
            if record.vehicule_id:
                record.dotation_carburant = len(record.vehicule_id) * record.carburant
            else:
                record.dotation_carburant = 0

    @api.depends('consommation_id', 'source')
    def _compute_cout_carburant(self):
        """
        Le coût carburant dépend du nombre de consommations,
        de la source (carte ou tickets) et du prix au litre.
        """
        for record in self:
            record.cout_carburant = 0
            if record.consommation_id:
                nombre_cons = len(record.consommation_id)
                if record.source == "Cart":
                    record.cout_carburant = nombre_cons * record.prix_littre * record.carburant
                    record.cout_ticket = 0
                else:
                    record.cout_carburant = record.cout_ticket * nombre_cons

    @api.depends("total_perdieme", "consommation_id", "moyen_transport")
    def _depends_cout_mission(self):
        """
        Calcule le coût total de la mission = perdieme + coût carburant (+ éventuellement coût ticket).
        """
        for record in self:
            if record.cout_carburant or record.cout_ticket:
                record.cout_mission = record.total_perdieme + record.cout_carburant + record.cout_ticket
            else:
                record.cout_mission = record.total_perdieme

    # -------------------------------------------------------------------------
    #                   ONCHANGE ET LOGIQUES DE FORMULAIRE
    # -------------------------------------------------------------------------

    @api.onchange('type_mission_id')
    def _onchange_zone_id(self):
        """
        Si la mission est de type 'intérieure', on vide la zone.
        """
        for record in self:
            if record.type_mission_id and record.type_mission_id.type_miss.lower() in [
                'interieur', 'intérieur', 'intérieure', 'interne'
            ]:
                record.zone_id = False

    @api.onchange("distance")
    def _onchange_carburant(self):
        """
        Approxime le carburant nécessaire : 15L pour 100km.
        """
        for record in self:
            record.carburant = 0
            if record.distance:
                record.carburant = (record.distance * 15) / 100.0

    @api.onchange("carburant", "source", "moyen_transport", "consommation_id")
    def _onchange_nombre_ticket(self):
        """
        Actualise le nombre de tickets en fonction de la quantité de carburant, de la source, etc.
        """
        for record in self:
            nombre_cons = len(record.consommation_id) if record.consommation_id else 1
            if record.carburant and record.source == "Ticket":
                record.nombre_ticket = ceil(record.carburant / 10) * nombre_cons
                record.cartecarburant_id = False
                record.cout_carburant = record.cout_ticket
            else:
                record.nombre_ticket = 0

    @api.onchange("cartecarburant_id", "moyen_transport")
    def _onchange_prix_littre(self):
        """
        Récupère le prix de la dernière recharge sur la carte sélectionnée.
        """
        for record in self:
            if record.cartecarburant_id and record.moyen_transport == "Voiture":
                chargements = record.cartecarburant_id.chargement_ids
                if chargements:
                    record.prix_littre = chargements[-1].prix
                else:
                    raise ValidationError(_("Veuillez charger la carte avant de l'utiliser."))

    @api.onchange("prix_littre", "nombre_ticket")
    def _onchange_cout_ticket(self):
        """
        Calcule le coût total des tickets (nombre de tickets * 10 litres * prix).
        """
        for record in self:
            record.cout_ticket = record.prix_littre * record.nombre_ticket * 10.0 if record.prix_littre else 0

    @api.onchange('vehicule_id', 'carburant', 'cartecarburant_id', 'prix_littre', 'source', 'moyen_transport')
    def _onchange_consommation_id(self):
        """
        Crée automatiquement les lignes de consommation (un record par véhicule).
        """
        for record in self:
            lines = [(5, 0, 0)]  # On vide d'abord les anciennes lignes
            if record.vehicule_id and record.moyen_transport == "Voiture":
                for veh in record.vehicule_id:
                    if record.source == "Cart":
                        consommation_record = {
                            'nb_littre': record.carburant,
                            'prix': record.prix_littre,
                            'total': record.prix_littre * record.carburant,
                            'vehicule_id': veh.voiture_id.id,
                            'delegation_id': record.id,
                            'carte_id': record.cartecarburant_id.id
                        }
                    else:
                        consommation_record = {
                            'nb_littre': record.carburant,
                            'prix': record.prix_littre,
                            'total': record.cout_ticket,
                            'vehicule_id': veh.voiture_id.id,
                            'delegation_id': record.id,
                            'carte_id': record.cartecarburant_id.id
                        }
                    lines.append((0, 0, consommation_record))

            # Pour les transports Avion, Bateau, Train, on supprime la carte, tickets etc.
            if record.moyen_transport in ['Avion', 'Bateau', 'Train']:
                record.cartecarburant_id = False
                record.nombre_ticket = 0
                record.prix_littre = 0
                record.source = ''
                self.env['mission.vehicle'].sudo().search([('mission_id', '=', record.id)]).unlink()

            record.consommation_id = lines

    @api.onchange("chef", "type_mission_id", "zone_id", "nb_nuit")
    def _onchange_equipe_id(self):
        """
        Ajoute automatiquement le chef dans l'équipe de mission si besoin.
        """
        for record in self:
            personal_equipe = [(5, 0, 0)]  # On supprime d'abord
            if not record.equipe_id:
                # Si aucune équipe, on l'initialise avec le chef
                if record.chef or record.nb_nuit:
                    personal_record = {
                        'employee_id': record.chef.id,
                        'mission_id': record.id,
                    }
                    personal_equipe.append((0, 0, personal_record))
            else:
                # On recrée l'équipe en remettant le chef au début
                if record.chef or record.nb_nuit:
                    first_type_missionnaire_id = record.equipe_id[0].type_missionnaire_id.id if record.equipe_id else False
                    personal_record_one = {
                        'employee_id': record.chef.id,
                        'type_missionnaire_id': first_type_missionnaire_id,
                        'mission_id': record.id,
                    }
                    personal_equipe.append((0, 0, personal_record_one))

                    for equipe in record.equipe_id[1::]:
                        personal_record = {
                            'employee_id': equipe.employee_id.id,
                            'type_missionnaire_id': equipe.type_missionnaire_id.id,
                            'mission_id': record.id,
                        }
                        personal_equipe.append((0, 0, personal_record))

            record.equipe_id = personal_equipe

    # -------------------------------------------------------------------------
    #                   METHODES CRUD / CREATE
    # -------------------------------------------------------------------------

    @api.model
    def create(self, values):
        """
        Crée la mission et lui affecte un numéro auto-généré via la séquence définie.
        """
        values["name"] = self.env["ir.sequence"].next_by_code("mission.delegation") or "/"
        res = super(Delegation, self).create(values)
        return res

    # -------------------------------------------------------------------------
    #                   METHODES DU WORKFLOW
    # -------------------------------------------------------------------------

    def action_programmer(self):
        self.write({'state': 'programmer'})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    def action_confirmer(self):
        self.write({'state': 'confirmer'})
        self.action_send_email_etat_mission("email_template_equipe_mission")
        self.action_send_email_etat_mission("etat_liquidatif_mission")
        self.action_send_email_etat_mission("etat_liquidatif_mission_compta")
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    def action_annuler(self):
        self.write({'state': 'annuler'})
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "disponible"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "disponible"})
        self.chef.write({'state': "disponible"})

    def action_en_cours(self):
        self.write({'state': 'en_cours'})
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.sudo().write({'state': "en_mission"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    def action_terminer(self):
        self.write({'state': 'terminer'})
        self.action_send_email_etat_mission("etat_liquidatif_mission")
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "disponible"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "disponible"})
        self.chef.write({'state': "disponible"})

    # -------------------------------------------------------------------------
    #                   METHODES D'IMPRESSION ET D'EXPORT
    # -------------------------------------------------------------------------

    def print_report_agent(self):
        return self.env.ref("mission.report_mission_delegation_agent").report_action(self)

    def print_report_mission(self):
        return self.env.ref("mission.report_mission_delegation").report_action(self)

    def import_data(self):
        return self.env.ref("odoo.addons.base_import.models.base_import.ImportRecords")

    # -------------------------------------------------------------------------
    #                   METHODES D'ENVOI PAR EMAIL
    # -------------------------------------------------------------------------

    def envoie_email_method(self):
        notif_message = "Email envoyé avec succès"
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        template = self.env.ref("mission.%s" % xml_id)
        if template:
            self.env["mail.template"].browse(template.id).sudo().send_mail(self.id, force_send=True)
            self.env["mail.mail"].sudo().process_email_queue()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': notif_message,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def action_send_email_etat_mission(self, temp):
        send_notification = "Email envoyé avec succès"
        template = self.env.ref("mission.%s" % temp)
        if template:
            self.env["mail.template"].browse(template.id).sudo().send_mail(self.id, force_send=True)
            self.env["mail.mail"].sudo().process_email_queue()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': send_notification,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    # -------------------------------------------------------------------------
    #                   METHODES UTILES
    # -------------------------------------------------------------------------

    def con_mission_state_method(self):
        """
        Méthode déclenchée (cron) pour basculer automatiquement l'état de la mission
        en 'en_cours' ou 'terminer' selon les dates du jour.
        """
        date_today = datetime.today().date()
        mission_programmers = self.env['mission.delegation'].sudo().search([('date_depart', '=', date_today)])
        for status_mission in mission_programmers:
            if status_mission.state == 'confirmer':
                status_mission.state = "en_cours"

        mission_en_cours = self.env['mission.delegation'].sudo().search([('date_retour', '=', date_today)])
        for status_mission in mission_en_cours:
            if status_mission.state == 'en_cours':
                status_mission.state = "terminer"
        return True

    def convert_number_to_words(self, avance):
        """
        Convertit un montant numérique en toutes lettres, en français.
        """
        number_text = num2words(avance, lang="fr")
        return number_text

    def get_manager(self, groupe):
        manager = []
        users = self.env['res.users'].sudo().search([])
        for user in users:
            if user.has_group(groupe):
                employe = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
                if employe:
                    manager.append(employe.work_email)
        return ';'.join(manager)

    def get_rh(self):
        return self.get_manager('mission.group_mission_rh')

    def get_daf(self):
        return self.get_manager('mission.group_mission_daf')

    def get_compta(self):
        return self.get_manager('mission.group_mission_comptability')

    def get_imputation_bugetaire(self):
        budgets = self.env['mission.budget'].sudo().search([])
        return budgets[-1].name if budgets else ""
