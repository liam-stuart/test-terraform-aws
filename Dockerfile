FROM public.ecr.aws/lambda/python:3.12
WORKDIR ${LAMBDA_TASK_ROOT}
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
USER 1000
CMD ["echo", "Python code successfully built!"]