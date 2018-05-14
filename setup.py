from setuptools import setup, find_packages

setup(name='adyen',
      version='0.1.3',
      description='Python library for the Adyen payment provider',
      license="MIT",
      author='Markus Bertheau',
      author_email='mbertheau@gmail.com',
      long_description=open('README.md').read(),
      packages=find_packages(),
      install_requires=['pytz', 'zope.dottedname'],
      classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: Implementation :: CPython'
            'Environment :: Web Environment',
            'Framework :: Django'
      ])
