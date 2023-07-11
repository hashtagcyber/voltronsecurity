# voltronsecurity
Python package for abstracting security findings


### Test
~~~
git clone https://github.com/hashtagcyber/voltronsecurity.git
cd voltronsecurity
coverage run -m unittest discover -v && coverage report -m --skip-empty --omit 'tests/*'
~~~

### Build
~~~
git clone https://github.com/hashtagcyber/voltronsecurity.git
cd voltronsecurity
python -m build
~~~
### Install
~~~
python -m pip install voltronsecurity
~~~

### Sample Deployment using RabbitMQ and K8s \(In Progress)
- [ ] sample rabbitmq host .yaml
- [ ] sample rabbitmq queues
    - inventory-snyk-orgs \(receives basic trigger message to inventory orgs)
    - inventory-snyk-projects \(receives snyk org to inventory projects of)
    - inventory-snyk-findings \(receives snyk project to inventory findings of)
    - inventory-wiz-tenant \(receives basic trigger message to inventory wiz projects)
    - inventory-wiz-findings \(receives wiz project to inventory findings of)
    - persist-snyk-findings
    - persist-wiz-findings
- [ ] sample snyk containers .yaml
    - [ ] 
- [ ] sample wiz containers .yaml
- [ ] sample metabase container .yaml
- [ ] sample psql container .yaml