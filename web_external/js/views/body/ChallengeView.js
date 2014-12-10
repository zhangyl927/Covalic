covalic.views.ChallengeView = covalic.View.extend({

    initialize: function (settings) {
        girder.cancelRestRequests('fetch');
        if (settings.challenge) {
            this.model = settings.challenge;
            this.render();
        } else if (settings.id) {
            this.model = new girder.models.ChallengeModel();
            this.model.set('_id', settings.id);

            this.model.on('g:fetched', function() {
               this.render();
            }, this).fetch();
        }
    },

    render: function() {
        this.$el.html(girder.templates.challengePage({
            challenge: this.model
        }));

        return this;
    }

});

girder.router.route('challenge/:id', 'challenge', function(id, params) {
    // Fetch the challenge by id, then render the view.
    var challenge = new girder.models.ChallengeModel();
    challenge.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', covalic.views.ChallengeView, params || {});
    }, this).on('g:error', function () {
        girder.router.navigate('challenges', {trigger: true});
    }, this).fetch();
});
