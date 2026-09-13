from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired
from app.models import CollaborationStatus, ReportStatus

from wtforms import ValidationError

def no_url_validator(message):
    def _no_url(form, field):
        if field.data:
            val = field.data.lower()
            if 'http://' in val or 'https://' in val or 'www.' in val:
                raise ValidationError(message)
    return _no_url


class AddCollaborationForm(FlaskForm):
    target_researcher_uuid = HiddenField('Target Researcher', validators=[DataRequired()])
    status = SelectField('Collaboration Status', choices=[
        (CollaborationStatus.ESTABLISHED.name, 'Established (Past completed works)'),
        (CollaborationStatus.ONGOING.name, 'Ongoing (Currently working together)')
    ], validators=[DataRequired()])
    submit = SubmitField('Add Collaboration')

class ReportCollaborationForm(FlaskForm):
    collaboration_id = HiddenField('Collaboration ID', validators=[DataRequired()])
    message = TextAreaField('Why is this collaboration incorrect?', validators=[DataRequired()])
    submit = SubmitField('Submit Report')

class ReportResearcherForm(FlaskForm):
    researcher_uuid = HiddenField('Researcher UUID', validators=[DataRequired()])
    message = TextAreaField('What information is incorrect?', validators=[DataRequired()])
    submit = SubmitField('Submit Correction Request')

from wtforms import IntegerField
from wtforms.validators import Optional, URL, Length

class EditMyProfileForm(FlaskForm):
    affiliation = StringField('Affiliation (Institute/Company)', validators=[Optional(), Length(max=255)])
    department = StringField('Department', validators=[Optional(), Length(max=255)])
    address = StringField('Address / Location', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=100)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    
    research_interests = TextAreaField('Research Interests', validators=[Optional()])
    
    phd_institute = StringField('PhD Institute', validators=[Optional(), Length(max=255)])
    phd_year = IntegerField('PhD Year', validators=[Optional()])
    
    website = StringField('Personal Website', validators=[Optional(), Length(max=255)])
    orcid = StringField('ORCID ID (e.g. 0000-0001-2345-6789)', validators=[Optional(), Length(max=50), no_url_validator('Please paste only the ORCID ID, not the full URL.')])
    arxiv_id = StringField('arXiv Author ID (e.g. smith_j_1)', validators=[Optional(), Length(max=50), no_url_validator('Please paste only the arXiv Author ID, not the full URL.')])
    google_scholar_url = StringField('Google Scholar URL', validators=[Optional(), Length(max=255)])
    
    submit = SubmitField('Save Profile')
