# -*- coding: utf-8 -*-
{
    'name': "Sacco Loans",
    'summary':"""Manage Sacco Loans""",
    'description':"""
           Sacco Management module for creating and managing loan information. This is an extension of sacco member
    """,
    'author':"Denis korir",
    'website':"http://www.tritel.co.ke",
    'category':"Sacco Management",
    'version':"1.0",
    'depends':['base','sacco_member'],
    'data':['template.xml',
            'views/loan_views.xml',
            'views/sequences.xml',
            'views/reports.xml',
            'views/wizards.xml',
            'views/bi.xml',],
    'demo':['demo.xml',],

    }
