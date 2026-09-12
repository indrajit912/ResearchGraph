from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Optional, Email

class ResearcherForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    emails = StringField('Emails (Comma separated, first is primary)', validators=[Optional()])
    
    affiliation = StringField('Affiliation', validators=[Optional()])
    department = StringField('Department', validators=[Optional()])
    
    address = StringField('Address', validators=[Optional()])
    city = StringField('City', validators=[Optional()])
    state = StringField('State', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])
    
    phd_institute = StringField('PhD Institute', validators=[Optional()])
    phd_year = IntegerField('PhD Year', validators=[Optional()])
    
    website = StringField('Website', validators=[Optional()])
    orcid = StringField('ORCID', validators=[Optional()])
    arxiv_id = StringField('arXiv ID', validators=[Optional()])
    google_scholar_url = StringField('Google Scholar URL', validators=[Optional()])
    
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Researcher')

class ResearcherEmailForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    is_primary = BooleanField('Primary Email')
    submit = SubmitField('Add Email')

from wtforms import SelectField
class EdgeForm(FlaskForm):
    researcher_a = SelectField('Researcher A', validators=[DataRequired()])
    researcher_b = SelectField('Researcher B', validators=[DataRequired()])
    status = SelectField('Collaboration Status', choices=[('ESTABLISHED', 'Established (Completed)'), ('ONGOING', 'Ongoing (Active)')], validators=[DataRequired()])
    submit = SubmitField('Create Edge')

class SlugEdgeForm(FlaskForm):
    slug_a = StringField('Vertex A (Slug)', validators=[DataRequired()])
    slug_b = StringField('Vertex B (Slug)', validators=[DataRequired()])
    status_slug = SelectField('Collaboration Status', choices=[('ESTABLISHED', 'Established (Completed)'), ('ONGOING', 'Ongoing (Active)')], validators=[DataRequired()])
    submit_slug = SubmitField('Create Edge via Slugs')
