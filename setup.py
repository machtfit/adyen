from distutils.core import setup

setup(name='adyen',
      version='0.1.3',
      description='Python library for the Adyen payment provider',
      license="MIT",
      author='Markus Bertheau',
      author_email='mbertheau@gmail.com',
      long_description=open('README.md').read(),
      packages=['adyen'],
      install_requires=['pytz'])
