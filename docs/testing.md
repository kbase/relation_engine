# Testing

## Unit testing

### Quick 

Ensure dependencies:
- make
- python 3.7 or higher (?)

```bash
python -m venv venv
source vevn/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
make unit-test
```


## Integration Testing

### Quick

Ensure have dependencies:
- make
- docker

```bash
make integration-tests
```