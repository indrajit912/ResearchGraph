from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class SearchForm(FlaskForm):
    q = StringField('Search Researchers (Name or Email)', validators=[DataRequired()])
    submit = SubmitField('Search')
