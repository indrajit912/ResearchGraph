from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired
from app.models import CollaborationStatus, ReportStatus

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
