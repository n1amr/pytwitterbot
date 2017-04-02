from setuptools import setup
from setuptools import find_packages

required_packages = [
    'tweepy', ]


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='pytwitterbot',
      version='0.1',
      description='Customizable twitter bot',
      url='http://github.com/n1amr/pytwitterbot',
      author='Amr Alaa',
      author_email='n1amr1@gmail.com',
      license='MIT',
      packages=find_packages(),
      include_package_data=True,
      install_requires=required_packages,
      entry_points={
          'console_scripts': [
              'pytbot = pytwitterbot.__main__:entry_point']},
      zip_safe=False)
