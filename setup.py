from distutils.core import setup

setup(name='adyen',
      version='0.0.8',
      description='Python library for the Adyen payment provider',
      license="MIT",
      author='Markus Bertheau',
      author_email='mbertheau@gmail.com',
      long_description=open('README.md').read(),
      packages=['adyen', 'django_adyen', 'django_adyen.templatetags',
                'oscar_adyen'],
      install_requires=['pytz', 'zope.dottedname'])
