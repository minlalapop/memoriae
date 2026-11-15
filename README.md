# Memoriae

**exploring human memory through cognitive experiments and  models**
How do we handle partial memory recall? Can neural networks make the same mistakes as we do? This is what Memoriae is all about. A small research project aiming to look at memory from the perspective of both humans and computational models. We ask people to run memory experiments, then ask models to try to complete similar tasks. We then compare how often they get things right, what they forget, get confused about and overall how they perform.

## What can it do?

Memoriae provides a web interface for researchers to:

- Design experiments with various cognitive tests + add participants and gather their responses
- Run the same experiments on compatible memory models
- Compare how well the models and humans performed using results and charts
There are various tests available:
-Verbal recall
-Visual and spatial memory
-Recognition
-Associative memory

##  model: Memoriae V2

The first model we have been looking at is an associative memory model using visual information. This model uses an autoencoder and a modern Hopfield style memory network. It was trained using the Fashion-MNIST dataset. The model learns to encode the images and store them in the associative memory. The model will then attempt to decode them when given partial information. To compare with humans we added a visual recognition task using the same images. There were three levels of masking: 25%, 50% and 75%. The participant will try to recognise the original image and V2 will attempt to retrieve the image from memory. The interesting thing is not necessarily which one performs better but understanding where they match and where they differ.

## getting started

Requires Python 3.12.

```bash
git clone https://github.com/minlalapop/memoriae.git
cd memoriae

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --constraint requirements.lock -e '.[test,dev,model]'
python -m app.setup

uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** in your browse

The setup command will ask you to create your researcher login.

built w : Python, FastAPI, PyTorch, SQLAlchemy, SQLite, and plain HTML, CSS and JavaScript + Docker

Fashion-MNIST is just the start. We want to add more memory models and experiments. Especially for cue recall, sequential memory and interference. Memoriae isn’t trying to show that neural networks have the same memory as humans but to experiment and test this theory. There is still a lot to do and it is still a work in progress.**
