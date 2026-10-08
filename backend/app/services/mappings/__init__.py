"""Mappings turn one provider's record of a call into a Connexity trace.

A mapping module is the only place allowed to know a provider's call format. Everything
downstream (storage, checks, the call screen, the assistant's tools) reads traces.
"""
