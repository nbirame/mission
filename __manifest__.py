# -*- coding: utf-8 -*-
{
    'name': "Mission",

    'summary': """
        Gestion des missions d'une entreprise""",

    'description': """
        Gestion des Missions d'entreprise
    """,

    'author': "Birame NDIAYE",
    'website': "https://nbirameblog.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Mission d\'entreprise',
    'version': '15.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'carburant', 'hr', 'fleet', 'mail', 'base_import'],

    # always loaded
    'data': [
        'security/mission_groupes.xml',
        'security/ir.model.access.csv',
        'wizard/sendEmail.xml',
        'views/zone_views.xml',
        'views/type_views.xml',
        'views/adresse_view.xml',
        'views/equipe_views.xml',
        'views/missionnaire_views.xml',
        'views/consommation_views.xml',
        'views/views.xml',
        'views/frais_views.xml',
        'views/indemnite_view.xml',
        'views/vehicule_views.xml',
        'views/voiture_views.xml',
        'views/suivi_essence_view.xml',
        # 'views/compagnie_view.xml',
        'views/odometre_view.xml',
        'data/sequence_mission.xml',
        'report/equippe_mission_report.xml',
        'report/equipe_mission_reprt_template.xml',
        'report/mission_report.xml',
        'report/mission_report_template.xml',
        'views/agent_views.xml',
        'report/ordre_mission_report.xml',
        'report/ordre_mission_report_template.xml',
        'report/report_ordre_agent.xml',
        'report/report_ordre_agent_mission_template.xml',
        'data/send_email.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
'assets': {
        'web.report_assets_common': [
            '/mission/static/src/scss/ordre.scss',
        ],
    },
}
