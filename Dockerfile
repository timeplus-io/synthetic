FROM python:3.12.10

WORKDIR /timeplus
ADD ./requirements.txt /timeplus/
RUN pip install -r requirements.txt
ADD ./main.py /timeplus/
ADD ./prompt/ /timeplus/prompt/
ADD ./static/ /timeplus/static/
ADD ./templates/ /timeplus/templates/

EXPOSE 5001

ENTRYPOINT ["python", "main.py"]